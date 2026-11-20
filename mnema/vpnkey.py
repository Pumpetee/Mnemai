"""Connect by a VPN key — the same link people paste into Hiddify, Happ or v2rayN: pick the service, then import the
key from the clipboard or type it in.

Mnemai carries Xray-core (vendor/xray, MPL-2.0, official build). A key becomes an Xray outbound; Xray listens on
127.0.0.1 as a local SOCKS proxy only for Mnemai, and Mnemai's proxy setting points there — chats with AI, search and
model downloads go through it. The rest of the computer is not touched: no system proxy, no adapter, no admin rights.

Keys understood:
- vless://   (tcp / ws / grpc / xhttp; tls or reality; xtls flow)
- vmess://   (base64 JSON)
- trojan://
- ss://      (SIP002 and the old base64 form)
- a subscription link https://… — its list is read and the first key that actually reaches the AI is taken.
The key is kept in the Windows secret store, never in the memory folder; the config Xray reads lives in ~/.mnema/xray
and is rewritten on every start.
"""

from __future__ import annotations

import atexit
import base64
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SCHEMES = ("vless://", "vmess://", "trojan://", "ss://")
_proc: dict = {"p": None, "port": 0, "name": ""}


def xray_exe() -> Path:
    if getattr(sys, "frozen", False):
        return (
            Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            / "xray"
            / ("xray.exe" if os.name == "nt" else "xray")
        )
    return Path(__file__).resolve().parents[1] / "vendor" / "xray" / ("xray.exe" if os.name == "nt" else "xray")


def home() -> Path:
    d = Path(os.environ.get("MNEMA_HOME") or Path.home() / ".mnema") / "xray"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _b64(s: str) -> str:
    s = s.strip().replace("-", "+").replace("_", "/")
    return base64.b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", "replace")


def _q(qs: dict, k: str, default: str = "") -> str:
    return unquote((qs.get(k) or [default])[0])


def _stream(net: str, security: str, q: dict, host_default: str) -> dict:
    net = net or "tcp"
    st: dict = {"network": net, "security": security or "none"}
    sni = q.get("sni") or q.get("host") or host_default
    if security == "tls":
        st["tlsSettings"] = {
            "serverName": sni,
            "fingerprint": q.get("fp") or "chrome",
            **({"alpn": q["alpn"].split(",")} if q.get("alpn") else {}),
        }
    elif security == "reality":
        st["realitySettings"] = {
            "serverName": sni,
            "fingerprint": q.get("fp") or "chrome",
            "publicKey": q.get("pbk", ""),
            "shortId": q.get("sid", ""),
            "spiderX": q.get("spx", ""),
        }
    if net == "ws":
        st["wsSettings"] = {"path": q.get("path") or "/", **({"headers": {"Host": q["host"]}} if q.get("host") else {})}
    elif net == "grpc":
        st["grpcSettings"] = {"serviceName": q.get("serviceName") or q.get("path") or ""}
    elif net in ("xhttp", "splithttp"):
        st["network"] = "xhttp"
        st["xhttpSettings"] = {
            "path": q.get("path") or "/",
            **({"host": q["host"]} if q.get("host") else {}),
            **({"mode": q["mode"]} if q.get("mode") else {}),
        }
    elif net == "tcp" and q.get("headerType") == "http":
        st["tcpSettings"] = {
            "header": {
                "type": "http",
                "request": {"path": [q.get("path") or "/"], "headers": {"Host": [q.get("host") or host_default]}},
            }
        }
    return st


def parse(key: str) -> dict:
    """A key → {"name", "outbound"} for Xray. ValueError with a plain message if it is not a key."""
    import re as _re

    try:
        return _parse(key)
    except ValueError as e:
        if _re.search(r"[А-Яа-яЁё]", str(e)):
            raise
        raise ValueError("ключ не читается: похоже, он скопирован не целиком — скопируй его ещё раз") from None
    except Exception:
        raise ValueError("ключ не читается: похоже, он скопирован не целиком — скопируй его ещё раз") from None


def _parse(key: str) -> dict:
    key = (key or "").strip()
    if key.startswith("vmess://"):
        try:
            d = json.loads(_b64(key[8:]))
        except Exception:
            raise ValueError("ключ vmess не читается")
        q = {
            "sni": d.get("sni", ""),
            "host": d.get("host", ""),
            "path": d.get("path", ""),
            "fp": d.get("fp", ""),
            "alpn": d.get("alpn", ""),
            "serviceName": d.get("path", ""),
            "headerType": d.get("type", ""),
        }
        out = {
            "protocol": "vmess",
            "settings": {
                "vnext": [
                    {
                        "address": d["add"],
                        "port": int(d["port"]),
                        "users": [
                            {"id": d["id"], "alterId": int(d.get("aid") or 0), "security": d.get("scy") or "auto"}
                        ],
                    }
                ]
            },
            "streamSettings": _stream(
                d.get("net", "tcp"), "tls" if d.get("tls") in ("tls", True) else "none", q, d["add"]
            ),
        }
        return {"name": d.get("ps") or d["add"], "outbound": out}
    if key.startswith("ss://"):
        body, _, name = key[5:].partition("#")
        if "@" in body:
            cred, _, hp = body.partition("@")
            cred = _b64(cred) if ":" not in cred else unquote(cred)
        else:
            dec = _b64(body.split("?")[0])
            cred, _, hp = dec.rpartition("@")
        method, _, password = cred.partition(":")
        host, _, port = hp.split("?")[0].split("/")[0].rpartition(":")
        if not (method and host and port):
            raise ValueError("ключ shadowsocks не читается")
        return {
            "name": unquote(name) or host,
            "outbound": {
                "protocol": "shadowsocks",
                "settings": {
                    "servers": [
                        {"address": host.strip("[]"), "port": int(port), "method": method, "password": password}
                    ]
                },
            },
        }
    if key.startswith(("vless://", "trojan://")):
        u = urlparse(key)
        q = {k: _q(parse_qs(u.query), k) for k in parse_qs(u.query)}
        if not (u.hostname and u.port and u.username):
            raise ValueError("в ключе нет адреса, порта или идентификатора")
        stream = _stream(
            q.get("type", "tcp"), q.get("security", "tls" if key.startswith("trojan") else "none"), q, u.hostname
        )
        if key.startswith("vless://"):
            user = {
                "id": unquote(u.username),
                "encryption": q.get("encryption") or "none",
                **({"flow": q["flow"]} if q.get("flow") else {}),
            }
            out = {
                "protocol": "vless",
                "settings": {"vnext": [{"address": u.hostname, "port": u.port, "users": [user]}]},
            }
        else:
            out = {
                "protocol": "trojan",
                "settings": {"servers": [{"address": u.hostname, "port": u.port, "password": unquote(u.username)}]},
            }
        out["streamSettings"] = stream
        return {"name": unquote(u.fragment) or u.hostname, "outbound": out}
    raise ValueError("это не ключ VPN: нужна ссылка vless://, vmess://, trojan://, ss:// или ссылка подписки https://")


def keys_from_subscription(url: str) -> list[str]:
    from . import net
    from .web import public_url
    import urllib.request

    if not public_url(url):
        raise ValueError("ссылка подписки должна вести на сервер в интернете (https://…)")

    try:
        raw = (
            net.urlopen(urllib.request.Request(url, headers={"User-Agent": "v2rayN/6"}), timeout=20)
            .read()
            .decode("utf-8", "replace")
            .strip()
        )
    except Exception as e:
        from .errors import human

        raise ValueError("ссылка подписки не открылась. " + human(e, "сервером подписки")) from None
    try:
        text = raw if any(s in raw for s in SCHEMES) else _b64(raw)
    except Exception:
        raise ValueError("по ссылке подписки нет ключей VPN — проверь ссылку") from None
    return [l.strip() for l in text.splitlines() if l.strip().startswith(SCHEMES)]


def _free_port(start: int = 10870) -> int:
    for p in range(start, start + 200):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("нет свободного порта для VPN")


def config(outbound: dict, port: int) -> dict:
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {"listen": "127.0.0.1", "port": port, "protocol": "socks", "settings": {"udp": True, "auth": "noauth"}}
        ],
        "outbounds": [{**outbound, "tag": "vpn"}, {"protocol": "freedom", "tag": "direct"}],
    }


def _forget_config() -> None:
    try:
        (home() / "config.json").unlink()
    except OSError:
        pass


def stop() -> None:
    _forget_config()
    p = _proc.get("p")
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(5)
        except Exception:
            p.kill()
    _proc.update(p=None, port=0, name="")


atexit.register(stop)


def start(outbound: dict, name: str = "") -> int:
    """Run Xray with this outbound; returns the local SOCKS port once it listens."""
    stop()
    exe = xray_exe()
    if not exe.exists():
        raise RuntimeError("в сборке нет движка VPN (Xray)")
    port = _free_port()
    cfg = home() / "config.json"
    cfg.write_text(json.dumps(config(outbound, port), ensure_ascii=False, indent=2), encoding="utf-8")
    log = (home() / "xray.log").open("w", encoding="utf-8")
    p = subprocess.Popen(
        [str(exe), "run", "-c", str(cfg)],
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=NO_WINDOW,
        cwd=str(exe.parent),
    )
    _proc.update(p=p, port=port, name=name)
    t = time.time()
    while time.time() - t < 8:
        if p.poll() is not None:
            log.close()
            _forget_config()
            err = (home() / "xray.log").read_text(encoding="utf-8", errors="replace")[-400:]
            raise RuntimeError("ключ не принят движком VPN: " + (err.strip().splitlines() or ["ошибка"])[-1])
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                _forget_config()  # read by now: the key lives only in the secret store and in Xray's memory
                return port
        time.sleep(0.2)
    _forget_config()
    raise RuntimeError("движок VPN не запустился")


def connect(vault, key: str, service: str = "") -> dict:
    """Parse, start, check that the AI is reachable through it, save. Subscription → the first key that works."""
    from . import net
    from .agent import profile as P
    from .learn import secrets_store
    from .learn.settings import _vid

    key = (key or "").strip()
    cands = keys_from_subscription(key) if key.startswith(("http://", "https://")) else [key]
    if not cands:
        raise ValueError("в подписке нет ключей, которые понимает Mnemai")
    last = ""
    for k in cands[:8]:
        try:
            d = parse(k)
            port = start(d["outbound"], d["name"])
            r = net.check(f"socks5://127.0.0.1:{port}", timeout=12)
            if r["ok"]:
                secrets_store.put(_vid(vault), "net.vpn_key", k)
                P.save(vault, {"vpn_key_on": True, "vpn_service": service, "vpn_name": d["name"], "vpn_error": ""})
                net.save(vault, f"socks5://127.0.0.1:{port}", "")
                return {"ok": True, "name": d["name"], "port": port, "ms": r["ms"], "tried": cands.index(k) + 1}
            last = (r["error"] or "нет связи") + " — сервер VPN не отвечает: проверь ключ или возьми другой"
        except (ValueError, RuntimeError) as e:
            last = str(e)
        stop()
    raise ValueError(f"не подключилось: {last} — введи ключ вручную или возьми другой")


def resume(vault) -> dict | None:
    """At start: the saved key is brought up again and the proxy pointed at it (the port may change)."""
    from . import net
    from .agent import profile as P
    from .learn import secrets_store
    from .learn.settings import _vid

    if not P.load(vault).get("vpn_key_on"):
        return None
    k = secrets_store.get(_vid(vault), "net.vpn_key")
    if not k:
        return None
    try:
        d = parse(k)
        port = start(d["outbound"], d["name"])
        P.save(vault, {"proxy": f"socks5://127.0.0.1:{port}"})
        net.load(vault)
        r = net.check(f"socks5://127.0.0.1:{port}", timeout=8)  # brought up is not the same as working
        if not r["ok"]:
            err = (
                f"VPN «{d['name']}» не отвечает ({r['error']}). Введи ключ вручную, возьми другой или выключи VPN — "
                "Настройки → VPN и прокси."
            )
            P.save(vault, {"vpn_error": err})
            return {"ok": False, "name": d["name"], "port": port, "error": err}
        P.save(vault, {"vpn_error": ""})
        return {"ok": True, "name": d["name"], "port": port}
    except Exception as e:
        P.save(vault, {"vpn_error": f"VPN не поднялся: {e}"})
        return {"ok": False, "error": str(e)}


def disconnect(vault) -> dict:
    from . import net
    from .agent import profile as P

    stop()
    P.save(vault, {"vpn_key_on": False, "vpn_error": ""})
    net.save(vault, "", "")
    return status(vault)


def status(vault) -> dict:
    from .agent import profile as P

    p = P.load(vault)
    on = bool(_proc.get("p") and _proc["p"].poll() is None)
    return {
        "on": on and bool(p.get("vpn_key_on")),
        "saved": bool(p.get("vpn_key_on")),
        "name": p.get("vpn_name", ""),
        "service": p.get("vpn_service", ""),
        "port": _proc.get("port", 0),
        "engine": xray_exe().exists(),
        "error": p.get("vpn_error", "") if p.get("vpn_key_on") else "",
    }
