"""Web surfing done on the computer, free and without keys: search, open pages, keep only what answers the question.

Search: free engines without keys, first relevant answer wins — Bing and Yahoo through the ddgs library (it talks
like a normal browser, so engines don't block it after a few queries), then DuckDuckGo, Bing and Wikipedia directly.
No paid search keys (the Brave key setting is gone since 1.4). Pages are downloaded and cleaned locally (docs.html_text),
then retrieve.best() picks the passages relevant to the question. The model gets a few numbered excerpts with
links — not whole pages — so it can answer and cite [1], [2] at a fraction of the tokens.
"""

from __future__ import annotations

import base64
import concurrent.futures as cf
import html as htmlmod
import json
import re
import urllib.parse
import urllib.request

from . import net
from .docs import html_text
from .retrieve import best

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
    "Accept-Language": "ru,en;q=0.8",
}
URL_IN_TEXT = re.compile(r"https?://[^\s<>\"')\]]+")


def public_url(url: str) -> bool:
    """http(s) to a public address: not this computer, not the home or office network, not a link-local address.
    A page a link points to is read only from the internet, never from inside."""
    import ipaddress
    import socket

    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    host = u.hostname.strip("[]").lower()
    if host in ("localhost",) or host.endswith((".local", ".localhost", ".internal", ".lan", ".home")):
        return False
    try:
        addrs = {ai[4][0] for ai in socket.getaddrinfo(host, None)}
    except OSError:
        return True  # not resolved here: through a proxy it is the proxy's name lookup, which is outside
    for a in addrs:
        ip = ipaddress.ip_address(a.split("%")[0])
        if not ip.is_global or ip.is_multicast:
            return False
    return True


def _open(url: str, direct: bool, timeout: int, data: bytes | None = None, headers: dict | None = None):
    if not public_url(url):
        raise ValueError("этот адрес внутри компьютера или локальной сети — такие Mnemai не открывает")
    # urllib refuses non-ASCII URLs; models and users pass Cyrillic Wikipedia links as-is
    parts = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            urllib.parse.quote(parts.path, safe="/%"),
            urllib.parse.quote(parts.query, safe="=&%+;"),
            urllib.parse.quote(parts.fragment, safe="%"),
        )
    )
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    if direct:
        return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)
    return net.urlopen(req, timeout=timeout)


def _get(
    url: str,
    timeout: int = 15,
    limit: int = 3_000_000,
    direct: bool | None = None,
    data: bytes | None = None,
    headers: dict | None = None,
) -> tuple[str, str]:
    """direct=None: through the owner's proxy, and straight if that fails (and the other way round)."""
    tries = [False, True] if direct is None else [direct]
    last = None
    for d in tries:
        try:
            with _open(url, d, timeout, data, headers) as r:
                ctype = r.headers.get("Content-Type", "")
                raw = r.read(limit)
            break
        except Exception as e:
            last = e
    else:
        raise last
    enc = re.search(r"charset=([\w-]+)", ctype)
    if not enc:
        enc = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", raw[:4000], re.I)
    name = (enc.group(1).decode() if isinstance(enc.group(1), bytes) else enc.group(1)) if enc else "utf-8"
    try:
        return raw.decode(name, "replace"), ctype
    except LookupError:
        return raw.decode("utf-8", "replace"), ctype


def _bing_url(href: str) -> str:
    href = htmlmod.unescape(href)
    if "bing.com/ck/a" in href:
        u = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("u", [""])[0]
        if u.startswith("a1"):
            b = u[2:] + "=" * (-len(u[2:]) % 4)
            try:
                return base64.urlsafe_b64decode(b).decode("utf-8", "replace")
            except Exception:
                return ""
    return href


def _ddg(query: str, direct: bool, lite: bool = False) -> list[dict]:
    if lite:
        raw, _ = _get(
            "https://lite.duckduckgo.com/lite/",
            direct=direct,
            data=urllib.parse.urlencode({"q": query, "kl": "ru-ru"}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*class=.result-link.[^>]*>(.*?)</a>', raw, re.S)
        snips = re.findall(r"<td class=.result-snippet.[^>]*>(.*?)</td>", raw, re.S)
    else:
        raw, _ = _get(
            "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query, "kl": "ru-ru"}), direct=direct
        )
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', raw, re.S)
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', raw, re.S)
    out = []
    for i, (href, title) in enumerate(links):
        href = htmlmod.unescape(href)
        if "uddg=" in href:
            href = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [""])[0])
        if href.startswith("//"):
            href = "https:" + href
        if href.startswith("http") and "duckduckgo.com/y.js" not in href:
            out.append(
                {
                    "title": htmlmod.unescape(re.sub(r"<[^>]+>", "", title)).strip(),
                    "url": href,
                    "snippet": htmlmod.unescape(re.sub(r"<[^>]+>", "", snips[i])).strip() if i < len(snips) else "",
                }
            )
    return out


def _bing(query: str, direct: bool) -> list[dict]:
    raw, _ = _get("https://www.bing.com/search?" + urllib.parse.urlencode({"q": query}), direct=direct)
    out = []
    for it in re.findall(r'<li class="b_algo"(.*?)</li>', raw, re.S):
        a = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', it, re.S)
        p = re.search(r"<p[^>]*>(.*?)</p>", it, re.S)
        if a and _bing_url(a.group(1)).startswith("http"):
            out.append(
                {
                    "title": htmlmod.unescape(re.sub(r"<[^>]+>", "", a.group(2))).strip(),
                    "url": _bing_url(a.group(1)),
                    "snippet": htmlmod.unescape(re.sub(r"<[^>]+>", "", p.group(1))).strip() if p else "",
                }
            )
    return out


def _relevant(query: str, results: list[dict]) -> list[dict]:
    """Search engines sometimes answer a bot with junk (films, casinos). Keep results sharing most of the key words."""
    import math
    from .retrieve import terms

    q = set(terms(query))
    need = max(1, math.ceil(len(q) * 0.6))
    return [
        r
        for r in results
        if len(q & set(terms(r["title"] + " " + r["snippet"] + " " + re.sub(r"[-_/.]", " ", r["url"])))) >= need
    ]


QUESTION_WORDS = set(
    "какой какая какое какие каков сколько почему зачем как когда где куда откуда кто что чем чего ли "
    "такое такой такая это скажи расскажи подскажи найди посмотри объясни хочу узнать нужно можно ли есть ей ним ней "
    "нового новое коротко кратко подробно вкратце фраза фразы фраз фразами ссылка ссылки ссылкой ссылками источник "
    "источники источниками абзац абзаца абзацем слово слова слов словами предложение предложения предложений списком "
    "ответь напиши дай пожалуйста две три пару несколько одной двух трёх трех интернете интернет поищи загугли "
    "please briefly short links sources".split()
)


def keywords(text: str, limit: int = 8) -> str:
    """A question → a search query: the question sentence if there is one, without question words, requests about the
    answer's form ("коротко, со ссылками") and filler. Names, numbers and versions stay."""
    from .retrieve import STOP

    text = URL_IN_TEXT.sub(" ", text).strip()
    asks = [x for x in re.split(r"(?<=[.!?])\s+", text) if x.rstrip().endswith("?")]
    base = " ".join(asks) if asks else text
    words = [w.strip(".") for w in re.findall(r"[\w.+#]+(?:-[\w.+#]+)*", base)]
    junk = STOP | QUESTION_WORDS
    keep = [w for w in words if len(w) > 1 and not all(x.lower() in junk for x in w.split("-"))]
    return " ".join(keep[:limit]) or text[:120]


_cache: dict[str, tuple[float, list]] = {}

# ---------------------------------------------------------------- when to search, and whom to trust

SMALL_TALK = re.compile(
    r"^\W*(привет|здравствуй|здравствуйте|добрый (день|вечер|утро)|доброе утро|как дела|как ты|как жизнь|что нового|"
    r"спасибо|благодарю|пока|ок|окей|хорошо|понятно|ясно|отлично|супер|да|нет|ага|угу|"
    r"hi|hello|hey|thanks|thank you|ok|okay|bye|how are you)\b",
    re.I,
)
ABOUT_ME = re.compile(r"\b(я|мне|меня|мной|мой|моя|моё|мои|моих|обо мне|про меня|my|me|mine|about me)\b", re.I)
ABOUT_YOU = re.compile(
    r"\b(ты|тебя|тебе|тобой|твой|твоя|твоё|твои|умеешь|можешь|сможешь|знаешь|mnema|мнем\w*|you|your|can you)\b", re.I
)
ASKS_WEB = re.compile(r"найди|поищи|загугли|в интернете|в сети|погугли|search|look up|google", re.I)
FACTUAL = re.compile(
    r"\?|что такое|кто такой|кто такая|сколько стоит|сколько|какой|какая|какие|когда|где|почему|зачем|"
    r"последн|сейчас|сегодня|новост|курс|цена|стоимость|версия|вышел|вышла|закон|правил|расписан|погода|"
    r"what|who|when|where|why|how much|price|latest|news|version",
    re.I,
)


NEEDS_FRESH = re.compile(
    r"курс\w*\s+(доллар|евро|юан|валют|рубл|биткоин|btc)|сколько стоит|стоимост|цен[аыуе]\b|погод|новост|"
    r"расписани|последн\w* верси|вышл[аои]|вышел|релиз|котировк|результат\w* (матча|выбор|игры)|"
    r"кто (сейчас|сегодня)|на сегодня|в 202\d|за 202\d",
    re.I,
)


def needs_web(text: str) -> bool:
    """With «Интернет» off: does this question really need fresh data from the web (prices, news, versions, events)?
    Then Mnemai answers what it knows and offers to switch the search on."""
    t = (text or "").strip()
    if not should_search(t):
        return False
    return bool(ASKS_WEB.search(t) or FRESH.search(t) or NEEDS_FRESH.search(t))


def should_search(text: str) -> bool:
    """«Интернет» allows searching; this decides whether this message needs it at all. The web is only for data that
    must be exact and current, never "just because". Small talk, questions about the owner or about
    Mnemai itself, general knowledge and tasks on given text don't; fresh outside facts (prices, rates, news, versions,
    schedules, "сейчас / последний") and an explicit "найди" do."""
    t = (text or "").strip()
    if not t or URL_IN_TEXT.search(t):
        return False  # a link is read anyway
    if ASKS_WEB.search(t):
        return True
    if SMALL_TALK.match(t) and len(re.findall(r"\w+", t)) <= 6:
        return False
    if len(keywords(t).split()) < 2:
        return False
    if ABOUT_YOU.search(t) and not NEEDS_FRESH.search(t):
        return False  # about Mnemai itself: it answers from its own knowledge
    if ABOUT_ME.search(t) and not FRESH.search(t):
        return False  # about the owner: memory knows better than the web
    return bool(NEEDS_FRESH.search(t) or (FRESH.search(t) and FACTUAL.search(t)))


# serious sources only: encyclopedias, official sites, science, major news, documentation
TRUSTED_DOMAINS = (
    "wikipedia.org",
    "britannica.com",
    "who.int",
    "un.org",
    "europa.eu",
    "oecd.org",
    "worldbank.org",
    "imf.org",
    "nature.com",
    "science.org",
    "sciencedirect.com",
    "springer.com",
    "arxiv.org",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "nih.gov",
    "cdc.gov",
    "nasa.gov",
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "ft.com",
    "bloomberg.com",
    "wsj.com",
    "nytimes.com",
    "theguardian.com",
    "economist.com",
    "forbes.com",
    "cnbc.com",
    "theverge.com",
    "techcrunch.com",
    "wired.com",
    "rbc.ru",
    "kommersant.ru",
    "vedomosti.ru",
    "interfax.ru",
    "tass.ru",
    "ria.ru",
    "forbes.ru",
    "rg.ru",
    "cbr.ru",
    "nalog.gov.ru",
    "consultant.ru",
    "garant.ru",
    "habr.com",
    "postnauka.ru",
    "nplus1.ru",
    "elementy.ru",
    "minfin.gov.ru",
    "gosuslugi.ru",
    "python.org",
    "mozilla.org",
    "developer.mozilla.org",
    "microsoft.com",
    "learn.microsoft.com",
    "apple.com",
    "google.com",
    "anthropic.com",
    "openai.com",
    "huggingface.co",
    "github.com",
    "postgresql.org",
    "docker.com",
    "kubernetes.io",
    "w3.org",
    "ietf.org",
    "iso.org",
    "investopedia.com",
    "statista.com",
    "mckinsey.com",
    "hbr.org",
    "gartner.com",
)
TRUSTED_TLD = (".gov", ".gov.ru", ".gov.uk", ".edu", ".ac.uk", ".ac.ru", ".int", ".mil")
TRUSTED_PREFIX = ("docs.", "developer.", "developers.", "learn.", "support.", "help.")


WIKI_LANGS = {"ru", "en", "zh", "es", "hi", "ar", "pt", "fr", "de", "ja", "www", "m"}


def trusted(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if not host:
        return False
    if any(host == d or host.endswith("." + d) for d in TRUSTED_DOMAINS):
        return True
    if any(host.endswith(t) for t in TRUSTED_TLD):
        return True
    return host.startswith(TRUSTED_PREFIX) and host.count(".") >= 2


FRESH = re.compile(
    r"последн|сейчас|сегодня|новост|свеж|актуальн|текущ|нынешн|в этом году|latest|current|today|news", re.I
)


def _wiki(query: str) -> list[dict]:
    """Wikipedia search API: always available, no key — the encyclopedic fallback."""
    import json as _json

    out = []
    for lang in ("ru", "en"):
        try:
            raw, _ = _get(
                f"https://{lang}.wikipedia.org/w/api.php?"
                + urllib.parse.urlencode(
                    {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 4}
                )
            )
            for it in _json.loads(raw).get("query", {}).get("search", []):
                out.append(
                    {
                        "title": it["title"] + " — Википедия" if lang == "ru" else it["title"] + " — Wikipedia",
                        "url": f"https://{lang}.wikipedia.org/wiki/"
                        + urllib.parse.quote(it["title"].replace(" ", "_")),
                        "snippet": htmlmod.unescape(re.sub(r"<[^>]+>", "", it.get("snippet", ""))),
                    }
                )
        except Exception:
            continue
    return out


def _brave(query: str) -> list[dict]:
    """Brave Search API — only when the owner put a key in settings."""
    import json as _json

    key = brave_key()
    if not key:
        return []
    raw, _ = _get(
        "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": 8}),
        headers={"X-Subscription-Token": key, "Accept": "application/json"},
    )
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": re.sub(r"<[^>]+>", "", r.get("description", "")),
        }
        for r in _json.loads(raw).get("web", {}).get("results", [])
    ]


_brave_key = {"v": ""}


def brave_key() -> str:
    return _brave_key["v"]


def set_brave_key(k: str) -> None:
    _brave_key["v"] = (k or "").strip()


def _ddgs_text(query: str, backend: str) -> list[dict]:
    """The ddgs library: free metasearch that talks to engines like a browser. Straight first, then through the proxy."""
    from ddgs import DDGS

    last = None
    for px in [None, net.proxy(net._setting["value"]) or None]:
        try:
            res = DDGS(proxy=px, timeout=8).text(query, max_results=8, backend=backend, region="ru-ru")
            return [
                {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
                for r in res
                if str(r.get("href", "")).startswith("http")
            ]
        except Exception as e:
            last = e
            if px is None and not net.proxy(net._setting["value"]):
                break
    raise last or RuntimeError("нет результатов")


ENGINES = [
    ("Brave", _brave),
    ("Bing", lambda q: _ddgs_text(q, "bing")),
    ("Yahoo", lambda q: _ddgs_text(q, "yahoo")),
    ("DuckDuckGo", lambda q: _ddgs_text(q, "duckduckgo")),
    ("DuckDuckGo", lambda q: _ddg(q, True)),
    ("DuckDuckGo lite", lambda q: _ddg(q, True, lite=True)),
    ("Bing", lambda q: _bing(q, True)),
    ("Яндекс", lambda q: _ddgs_text(q, "yandex")),
    ("Википедия", _wiki),
]


FACTUAL = re.compile(
    r"\b(?:когда|кто|что такое|родил(?:ся|ась|ись)?|умер(?:ла)?|столиц|сколько|где находится|"
    r"какой|какая|какое|дата|биограф|истори|изобрел|написал|основал)\b",
    re.I,
)


def search(query: str, n: int = 6) -> list[dict]:
    """[{title, url, snippet, engine}] — first engine that gives relevant results wins. Cached for 30 minutes."""
    import time as _t

    original = (query or "").strip()
    fresh = FRESH.search(original) and not re.search(r"\b20\d\d\b", original)
    query = keywords(original)
    if fresh:  # "latest / today / news": engines rank old pages high otherwise
        import datetime as _dt

        query += f" {_dt.date.today().year}"
    hit = _cache.get(query)
    if hit and _t.time() - hit[0] < 1800:
        return hit[1][:n]
    if not fresh and FACTUAL.search(original):
        # Encyclopedic questions have a fast, reliable answer; don't wait for several web engines.
        subject = re.split(r"[.!?]\s*", original.strip())[0]
        subject = re.sub(
            r"^(?:когда|кто|что такое|сколько|где находится|какой|какая|какое|дата|биография|"
            r"это|такой|такая|такое)\s+",
            "",
            subject,
            flags=re.I,
        )
        subject = re.sub(r"\b(?:родился|родилась|родились|умер|умерла|появился|появилась)\b", "", subject, flags=re.I)
        subject = " ".join(subject.split()).strip(" ?.,!") or query
        wiki = [r for r in _wiki(subject) if trusted(r["url"])]
        if wiki:
            _cache[query] = (_t.time(), wiki)
            return wiki[:n]
    res = _search_once(query, n)
    if res:
        _cache[query] = (_t.time(), res)
    return res


def _search_once(query: str, n: int) -> list[dict]:
    import queue
    import threading
    import time as _t

    def one(item):
        name, fn = item
        try:
            return name, _relevant(query, fn(query))
        except Exception:
            return name, []

    def keep(name: str, res: list[dict]) -> list[dict]:
        res = [r for r in res if trusted(r["url"])]
        per, out = {}, []
        for r in res:
            host = (urllib.parse.urlparse(r["url"]).hostname or "").lower()
            if (host == "wikipedia.org" or host.endswith(".wikipedia.org")) and host.split(".")[0] not in WIKI_LANGS:
                continue
            site = ".".join(host.split(".")[-2:])
            per[site] = per.get(site, 0) + 1
            if per[site] <= 2:
                out.append(r)
        seen, uniq = set(), []
        for r in out:
            if r["url"] not in seen:
                seen.add(r["url"])
                uniq.append({**r, "engine": name})
        return uniq[:n]

    # Daemon threads: a blocked engine never delays the answer and never keeps Python alive at exit.
    answers: queue.Queue = queue.Queue()
    for item in ENGINES:
        threading.Thread(target=lambda it=item: answers.put(one(it)), daemon=True, name="mnema-web").start()
    deadline = _t.time() + 5.0
    while _t.time() < deadline:
        try:
            name, res = answers.get(timeout=max(0.1, deadline - _t.time()))
        except queue.Empty:
            break
        uniq = keep(name, res)
        if uniq:
            return uniq
    return []


def fetch(url: str) -> dict:
    """{url, title, text} of a page, read and cleaned locally."""
    # Wikipedia's full page is huge; the summary API answers encyclopedic facts in a fraction of a second.
    parts = urllib.parse.urlsplit(url)
    if parts.hostname and parts.hostname.endswith("wikipedia.org") and "/wiki/" in parts.path:
        title = urllib.parse.unquote(parts.path.split("/wiki/", 1)[1]).replace("_", " ")
        try:
            api = f"https://{parts.hostname}/w/api.php?" + urllib.parse.urlencode(
                {
                    "action": "query",
                    "prop": "extracts",
                    "exintro": 1,
                    "explaintext": 1,
                    "redirects": 1,
                    "titles": title,
                    "format": "json",
                }
            )
            raw, _ = _get(api, timeout=8)
            pages = json.loads(raw).get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {})
            text = str(page.get("extract") or "").strip()
            if text:
                return {"url": url, "title": page.get("title") or title, "text": text}
        except Exception:
            pass
    raw, ctype = _get(url)
    if "html" not in ctype and not raw.lstrip().startswith("<"):
        return {"url": url, "title": url, "text": raw[:200_000]}
    title, text = html_text(raw)
    return {"url": url, "title": title or url, "text": text}


def gather(
    query: str, urls: list[str] | None = None, pages: int = 4, budget: int = 7000, search_too: bool = False
) -> dict:
    """Search (unless urls are given), read pages in parallel, keep the relevant passages.
    Returns {"context": text for the model, "sources": [{title, url}], "read_chars": all text read locally}."""
    found = [{"url": u, "title": u, "snippet": ""} for u in (urls or [])]
    if not urls or search_too:
        found += [r for r in search(query, n=pages + 2) if r["url"] not in (urls or [])]
        pages += len(urls or [])
    sources, blocks, read = [], [], 0
    per = max(1200, budget // max(1, min(pages, len(found)) or 1))
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda r: _safe_fetch(r), found[: pages + 2]))
    for r, page in zip(found, results):
        if len(sources) >= pages:
            break
        text = (page or {}).get("text") or r.get("snippet", "")
        if len(text) < 80:
            continue
        read += len(text)
        excerpt, _ = best(query, text, budget=per, head=300)
        sources.append({"title": (page or {}).get("title") or r["title"], "url": r["url"]})
        blocks.append(f"[{len(sources)}] {sources[-1]['title']} — {r['url']}\n{excerpt}")
    return {"context": "\n\n".join(blocks), "sources": sources, "read_chars": read}


def _safe_fetch(r: dict) -> dict | None:
    try:
        return fetch(r["url"])
    except Exception:
        return None
