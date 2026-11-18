# Architecture

[Русская версия](ARCHITECTURE.ru.md) · [Разбор по клиентскому пути](CLIENT_JOURNEY.md)

## Processes

```
Mnemai.exe (mnema/desktop.py)
 ├─ window: pywebview on Microsoft WebView2 → http://127.0.0.1:<port>/
 ├─ tray icon (pystray): open, learn now, pause, proxy, autostart, exit
 ├─ local API (mnema/api.py, a thread): the interface and the window's hooks
 ├─ learner (mnema/learn/engine.py, a thread): reads the allowed sources on a timer
 └─ llama-server (vendor/llama, a child process, only while a local model is used)

mnemai-cli.exe / python -m mnema (mnema/cli.py)
 └─ mcp — MCP server over stdio for Claude Code, Claude Desktop, Cursor
```

One copy per user (a named mutex); a second launch only shows the first window. Exit stops the learner, the tray icon and the window; `GET /api/app/quit` does the same for scripts.

## The memory folder

Plain Markdown, readable without Mnemai. Layout constants and access scopes are in `mnema/vault.py`.

| Path | Scope | Content |
|---|---|---|
| `00 Inbox/Inbox.md` | inbox | facts not sorted yet |
| `10 Now.md` | — | generated summary for today |
| `20 Projects/<name>/_Project.md` | projects | status, goal, journal of the project |
| `30 People/<name>.md` | people | one card per person |
| `60 Events/YYYY-MM.md` | decisions | decisions and status changes, newest first |
| `70 Memory/Profile.md`, `Rules.md`, `Thoughts.md` | profile, rules, notes | who the owner is, how to work with him |
| `70 Memory/Cards/<topic>.md` | cards | one card per topic; `#money`, `#health`, `#private` tags hide a heading |
| `70 Memory/Fact archive/` | — | replaced facts, never sent to a model |
| `90 System/Journal/`, `90 System/Recipes/` | — | readable journal, recipes of repeated tasks |
| `95 Saves/` | — | a copy before the first change of the day |
| `.mnema/` | — | access rules, journal with snapshots, tokens, learning state, chats |

A fact is one line with its date. A status line carries `(статус ДД.ММ.ГГГГ)`; a newer status of the same thing replaces the old one in place, the old one goes to the fact archive and the change to the event feed (`memory.remember`, `memory._put_fact`).

## Who sees what

`mnema/clients.py` holds one `Client` per AI: the scopes it reads, the scopes it may write, the tags it never sees, on/off. `memory.context_for(vault, client)` builds the context from that alone, so the chat, MCP and the extension share one rule. Cloud providers in the chat map to their client (`chat/providers.py` → `PROVIDERS[...]["client"]`); a model on this computer sees everything because nothing leaves it.

## A chat message

```
interface (ui/js/19-chat.js) ──POST /api/chat/send──▶ chat/engine.send
  1. the message is saved; learning on it starts in the background (learn/engine.learn_episodes)
  2. system prompt = behaviour rules (agent/profile.py) + memory this model may see (context_for)
                     + how Mnemai works now (chat/selfknow.py) + knowledge-base sections if the question is about Mnemai
  3. attached files: text extracted on the computer (docs.py); scans and images go as files where supported
  4. web: only when the question needs fresh outside data (web.should_search), pages read locally
  5. cloud model: secrets replaced with labels (outgoing.py), the request logged; local model: as is
  6. the answer streams back; labels restored; an ```ask block becomes buttons; term glossary cut off
interface polls /api/chat/poll and renders
```

The consortium (`chat/consortium.py`) runs 2–4 models in turns with a format (council, debate, brainstorm, red team), roles, a chosen summarizer and a length limit; every speaker gets memory under its own access rules.

## Learning

```
sources (learn/sources.py, learn/sources_life.py)  → Episode(source, ref, ts, text)
  only those switched on and allowed: settings.allowed() — "only Mnemai" blocks everything outside it
brain (learn/brains.py): explicit signals, Claude Code, an API key, or a local model → candidate facts
ledger (learn/ledger.py): repeats raise confidence; the day it was said (said_at) is kept
decision (learn/engine.decide_why): write / ask / wait / skip, with the reason shown in the feed
write: memory.remember(..., said=day) → journal, Now, Index regenerated
```

There is no waiting queue. From a conversation in Mnemai, a personal fact or a contradiction is asked once, right under that conversation (`chat["learn_ask"]`, answered through `/api/learn/review`); from anywhere else Mnemai decides by itself: personal goes to a hidden part, the newer fact replaces the older one (the old one goes to the fact archive), a weak guess waits to be seen again. Undoing a learned write means "no" for good.

## What leaves the computer

`outgoing.py` swaps card numbers (Luhn-checked), passwords, API keys, tokens, phone, passport and SNILS numbers for labels before any cloud request and puts the real values back into the streamed answer. Every cloud request is a line in `.mnema/outgoing.jsonl`: when, to whom, why, how much memory of how much available, what was hidden (counts only).

## Interface

`mnema/ui/index.html` is the page shell; `css/app.css` the styles; `js/NN-*.js` classic scripts loaded in numeric order and sharing one global scope (`01-core.js` helpers first, `29-navigation.js` and `30-boot.js` last, because they run at load and call into the rest). Texts are written in Russian; `ui/i18n/<lang>.json` holds nine more languages, applied by walking the page.

## Tests

`tests/` — unit tests without network or real models (providers, search and brains are faked). `tools/qa/` — a click-through of the real interface on a throw-away memory. GitHub Actions run lint, format, unit tests and the interface checks on every push (`.github/workflows/tests.yml`).
