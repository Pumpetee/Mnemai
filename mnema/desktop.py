"""Mnemai as a program: its own window, an icon in the tray (the menu bar on macOS), starts at login if you want,
learns in the background. Windows, macOS and Linux.

Closing the window hides it — learning goes on. "Выход" in the tray menu stops everything.
The window is pywebview: WebView2 on Windows, WebKit on macOS, Qt WebEngine on Linux. The tray is pystray on Windows
and macOS and Qt's own tray on Linux. The core works without any of them.
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import time
import socket
import sys
import threading
import urllib.request
from pathlib import Path

import webview
from PIL import Image, ImageDraw

from . import __version__, api, osapi as OS
from .cli import CONFIG, HOME
from .demo import make_demo
from .learn import engine, settings as S
from .learn.ledger import Ledger
from .memory import init_vault, token
from .vault import Vault
from .fsutil import read_json, write_json

APP = "Mnemai"


# ---------------------------------------------------------------- small helpers


def icon_image(size: int = 64) -> Image.Image:
    """The mark: an M on the violet square, two eyes over its outer legs. Drawn 4× and scaled down for smooth edges."""
    k = 4
    n = size * k
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=n // 4, fill=(99, 94, 230, 255))
    u = n / 24 * 0.62  # the 24-unit drawing, 62 % of the square
    o = (n - 24 * u) / 2
    p = lambda x, y: (o + x * u, o + y * u)  # noqa: E731
    w = max(2, round(2.7 * u))
    dot = lambda x, y, r: d.ellipse([x - r, y - r, x + r, y + r], fill="white")  # noqa: E731
    for seg in ([p(5, 19.5), p(5, 9.6)], [p(5.6, 6.8), p(12, 14.2), p(18.4, 6.8)], [p(19, 9.6), p(19, 19.5)]):
        d.line(seg, fill="white", width=w, joint="curve")
        for x, y in seg:
            dot(x, y, w / 2)
    for cx in (5, 19):  # the outer corners are the eyes
        dot(*p(cx, 6.6), 2.5 * u)
    return img.resize((size, size), Image.LANCZOS)


def free_port(start: int = 7461) -> int:
    for p in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("нет свободного порта")


def autostart_enabled() -> bool:
    return OS.autostart_enabled()


def set_autostart(on: bool) -> None:
    OS.set_autostart(on)


AUTOSTART_LABEL = {"windows": "Запускать вместе с Windows", "macos": "Открывать при входе в macOS"}.get(
    OS.NAME, "Запускать при входе в систему"
)


def load_config() -> dict:
    return read_json(CONFIG, {}) or {}


def save_config(cfg: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    write_json(CONFIG, cfg, indent=2)


# ---------------------------------------------------------------- single instance


def already_running() -> bool:
    """One copy at a time (a named mutex on Windows, a locked file elsewhere): the second launch just asks the first
    one to show its window."""
    if OS.first_instance(HOME):
        return False
    cfg = load_config()
    if cfg.get("vault") and cfg.get("port"):
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{cfg['port']}/api/app/show", headers={"X-Mnema-Token": token(Vault(cfg["vault"]))}
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass
    return True


def purge_dead_tray_icons() -> None:
    """Icons of processes killed by force stay in the tray until the mouse passes over them.
    Sweep a fake mouse move over both tray areas so Explorer drops them now."""
    if not OS.IS_WIN:
        return
    try:
        u = ctypes.windll.user32
        u.FindWindowW.restype = u.FindWindowExW.restype = ctypes.c_void_p
        areas = []
        h = u.FindWindowW("Shell_TrayWnd", None)
        for cls in ("TrayNotifyWnd", "SysPager", "ToolbarWindow32"):
            h = u.FindWindowExW(ctypes.c_void_p(h), None, cls, None) if h else None
        areas.append(h)
        h = u.FindWindowW("NotifyIconOverflowWindow", None)
        areas.append(u.FindWindowExW(ctypes.c_void_p(h), None, "ToolbarWindow32", None) if h else None)
        for h in filter(None, areas):
            r = (ctypes.c_long * 4)()
            u.GetClientRect(ctypes.c_void_p(h), r)
            for y in range(0, r[3], 4):
                for x in range(0, r[2], 4):
                    u.SendMessageW(ctypes.c_void_p(h), 0x0200, 0, (y << 16) | x)  # WM_MOUSEMOVE
    except Exception:
        pass


# ---------------------------------------------------------------- first launch

SETUP_HTML = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>
body{margin:0;font:15px/1.55 "Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--ink);display:grid;place-items:center;min-height:100vh}
.box{width:620px;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:34px 38px}
.brand{display:flex;gap:10px;align-items:center;font-weight:700;font-size:18px;margin-bottom:18px}.brand i{width:30px;height:30px;border-radius:9px;background:var(--acc);position:relative}.brand i::after,.brand i::before{content:'';position:absolute;inset:19%;background:center/contain no-repeat}.brand i::after{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M5 19.5V9.6M5.6 6.8L12 14.2l6.4-7.4M19 9.6v9.9' fill='none' stroke='%23fff' stroke-width='2.7' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")}.brand i::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Ccircle cx='5' cy='6.6' r='2.5' fill='%23fff'/%3E%3Ccircle cx='19' cy='6.6' r='2.5' fill='%23fff'/%3E%3C/svg%3E");transform-origin:50% 27.5%;animation:blink 7s infinite 2s}@keyframes blink{0%,93%,97%,100%{transform:none}95%{transform:scaleY(.12)}}
h1{font-size:26px;margin:0 0 8px}p{color:var(--ink2);margin:0 0 18px}
.opt{border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:12px}.opt b{font-size:16px}.opt .h{font-size:13px;color:var(--ink3);margin:4px 0 10px}
.row{display:flex;gap:8px}input{flex:1;border:1px solid var(--line);border-radius:10px;padding:8px 10px;font:inherit;font-size:14px}
button{border:0;border-radius:10px;padding:9px 16px;font:inherit;font-size:14px;font-weight:600;cursor:pointer;background:var(--acc);color:#fff}button.l{background:var(--acc2);color:var(--acc)}
#err{color:#c2413d;font-size:13px;margin-top:8px}
input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]),textarea,[contenteditable=true]{caret-color:var(--acc);cursor:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='24' viewBox='0 0 16 24'%3E%3Cpath d='M4.5 3h7M8 3v18M4.5 21h7' fill='none' stroke='white' stroke-width='4.2' stroke-linecap='round'/%3E%3Cpath d='M4.5 3h7M8 3v18M4.5 21h7' fill='none' stroke='%2316181d' stroke-width='1.7' stroke-linecap='round'/%3E%3C/svg%3E") 8 12,text}
details.opt summary{cursor:pointer;font-weight:600;font-size:15px;list-style:none}details.opt summary::-webkit-details-marker{display:none}
details.opt summary::after{content:' ▾';color:var(--ink3)}.px{display:grid;grid-template-columns:120px 1fr 90px;gap:8px;margin-top:10px}
.px2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}select{border:1px solid var(--line);border-radius:10px;padding:8px;font:inherit;font-size:14px;background:var(--card)}
#pxr{font-size:13px;margin-top:8px;color:var(--ink2)}
.vg{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:6px}
.vg button{position:relative;display:flex;flex-direction:column;align-items:flex-start;gap:1px;background:var(--card);color:var(--ink);border:1px solid var(--line);padding:9px 10px;font-weight:600;font-size:13px;text-align:left}
.vg button:hover{border-color:var(--acc)}.vg button.sel{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}.vg button small{font-weight:500;font-size:11px;color:var(--ink3)}
.vg button i{position:absolute;top:9px;right:9px;width:8px;height:8px;border-radius:50%;background:var(--line)}.vg button.live i{background:#1f8a4c}
.vr{display:flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid var(--line);border-radius:12px;margin-top:8px;font-size:13.5px;animation:up .25s ease}.vr b{font-weight:600}.vr small{color:var(--ink3)}.vr button{margin-left:auto;padding:6px 12px;font-size:13px}
.vr.ok{border-color:var(--okl);background:var(--okb)}.vr.sys{border-color:var(--acc3);background:var(--acc2)}.vr i{width:9px;height:9px;border-radius:50%;background:#1f8a4c;flex:none}
@keyframes up{from{opacity:0;transform:translateY(6px)}}
/* ---------- first launch: a little show */
body{overflow:hidden}
.bg{position:fixed;inset:0;pointer-events:none;overflow:hidden}.bg i{position:absolute;border-radius:50%;filter:blur(40px);opacity:.55;animation:drift 14s ease-in-out infinite}
.bg i:nth-child(1){width:380px;height:380px;background:#c9c6ff;left:-80px;top:-60px}.bg i:nth-child(2){width:320px;height:320px;background:#bfe3ff;right:-60px;bottom:-40px;animation-delay:-5s}.bg i:nth-child(3){width:220px;height:220px;background:#ffd9ef;right:20%;top:-80px;animation-delay:-9s}
@keyframes drift{50%{transform:translate(40px,30px) scale(1.12)}}
.splash{position:fixed;inset:0;display:grid;place-items:center;z-index:5;background:var(--bg);animation:splashout .5s ease 1.9s forwards}
.splash>div{display:flex;flex-direction:column;align-items:center;text-align:center;min-width:240px}.splash .lg{margin:0 auto;flex:none;width:84px;height:84px;border-radius:24px;background:linear-gradient(135deg,#6366f1,#8b5cf6);position:relative;box-shadow:0 18px 40px rgba(91,91,214,.35);animation:lgin 1s cubic-bezier(.2,1.4,.3,1) both}
.splash .lg::after,.splash .lg::before{content:'';position:absolute;inset:19%;background:center/contain no-repeat}.splash .lg::after{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M5 19.5V9.6M5.6 6.8L12 14.2l6.4-7.4M19 9.6v9.9' fill='none' stroke='%23fff' stroke-width='2.7' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");animation:lgspin 1.2s cubic-bezier(.5,0,.2,1) .3s both}.splash .lg::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Ccircle cx='5' cy='6.6' r='2.5' fill='%23fff'/%3E%3Ccircle cx='19' cy='6.6' r='2.5' fill='%23fff'/%3E%3C/svg%3E");animation:lgspin 1.2s cubic-bezier(.5,0,.2,1) .3s both}
.splash .wm{margin-top:18px;font-size:30px;font-weight:800;letter-spacing:.02em;display:flex;justify-content:center}.splash .wm span{display:inline-block;opacity:0;animation:letter .45s cubic-bezier(.2,1.3,.3,1) forwards}
.splash .tg{margin-top:6px;color:var(--ink2);font-size:14px;text-align:center;opacity:0;animation:fadeup .5s ease 1.2s forwards}
@keyframes lgin{0%{transform:scale(0) rotate(-200deg)}100%{transform:none}}@keyframes lgspin{from{transform:rotateY(180deg) scale(.4);opacity:0}to{transform:none;opacity:1}}
@keyframes letter{from{opacity:0;transform:translateY(14px) scale(.8)}to{opacity:1;transform:none}}@keyframes fadeup{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes splashout{to{opacity:0;visibility:hidden}}
.box{position:relative;opacity:0;animation:boxin .6s cubic-bezier(.2,.9,.2,1) 2s forwards}@keyframes boxin{from{opacity:0;transform:translateY(24px) scale(.97)}to{opacity:1;transform:none}}
.brand i{animation:hop 4s ease-in-out 3s infinite}@keyframes hop{0%,86%,100%{transform:none}90%{transform:translateY(-6px) rotate(-12deg)}94%{transform:translateY(0) rotate(6deg)}}
.dots{display:flex;gap:6px;margin-left:auto}.dots b{width:26px;height:6px;border-radius:4px;background:var(--line);overflow:hidden;position:relative}.dots b::after{content:'';position:absolute;inset:0;background:var(--acc);transform:scaleX(0);transform-origin:left;transition:transform .5s cubic-bezier(.2,.9,.2,1)}.dots b.on::after{transform:none}
.step:not([hidden]){animation:stepin .45s cubic-bezier(.2,.9,.2,1)}.step.back:not([hidden]){animation:stepback .45s cubic-bezier(.2,.9,.2,1)}
@keyframes stepin{from{opacity:0;transform:translateX(30px)}}@keyframes stepback{from{opacity:0;transform:translateX(-30px)}}
.langs button{opacity:0;animation:cardin .4s cubic-bezier(.2,1.2,.3,1) forwards}.langs button:hover .flag{animation:wave .8s ease-in-out infinite}
@keyframes cardin{from{opacity:0;transform:translateY(10px) scale(.95)}to{opacity:1;transform:none}}@keyframes wave{0%,100%{transform:skewY(0)}25%{transform:skewY(-6deg)}75%{transform:skewY(6deg)}}
.langs button.on .flag{animation:pop .4s cubic-bezier(.2,1.6,.3,1)}@keyframes pop{50%{transform:scale(1.35)}}
.hello{display:flex;align-items:center;gap:10px;min-height:34px;margin:-6px 0 6px;font-size:18px;font-weight:700;color:var(--acc)}.hello .hand{display:inline-block;transform-origin:70% 80%;animation:handwave 1.6s ease-in-out infinite}
@keyframes handwave{0%,60%,100%{transform:rotate(0)}10%,30%{transform:rotate(16deg)}20%,40%{transform:rotate(-8deg)}}
.hello .nm{display:inline-block;animation:pop .35s ease}
.memart{display:flex;justify-content:center;margin:2px 0 12px}.memart svg{width:150px;height:76px}
.memart .f{animation:fly 3.2s ease-in-out infinite}.memart .f2{animation-delay:1s}.memart .f3{animation-delay:2s}
@keyframes fly{0%{transform:translate(0,0);opacity:0}15%{opacity:1}60%{transform:translate(54px,22px) scale(.6);opacity:1}75%,100%{transform:translate(54px,22px) scale(.4);opacity:0}}
.party{position:fixed;inset:0;z-index:9;display:grid;place-items:center;background:color-mix(in srgb,var(--bg) 86%,transparent);backdrop-filter:blur(3px);animation:fadeup .3s ease}
.party .md{width:120px;height:120px;border-radius:50%;margin:0 auto;display:grid;place-items:center;background:radial-gradient(circle at 35% 30%,#fff7c9,#ffcf4a 55%,#f0a21b);box-shadow:0 18px 46px rgba(240,162,27,.45),inset 0 -6px 14px rgba(0,0,0,.12);font-size:54px;animation:medal 1s cubic-bezier(.2,1.5,.3,1) both}
.party .md::before{content:'';position:absolute;width:150px;height:150px;border-radius:50%;border:3px dashed #ffcf4a;animation:spinr 6s linear infinite}
@keyframes medal{0%{transform:scale(0) rotate(-180deg)}100%{transform:none}}@keyframes spinr{to{transform:rotate(360deg)}}
.party .t1{margin-top:22px;text-align:center;font-size:12px;letter-spacing:.12em;font-weight:800;color:#8a6d1a;text-transform:uppercase;opacity:0;animation:fadeup .4s ease .5s forwards}
.party .t2{text-align:center;font-size:26px;font-weight:800;margin-top:4px;opacity:0;animation:fadeup .4s ease .65s forwards}.party .t3{text-align:center;color:var(--ink2);margin-top:4px;opacity:0;animation:fadeup .4s ease .8s forwards}
.party .xp{display:inline-block;margin-top:10px;padding:4px 12px;border-radius:999px;background:var(--acc2);color:var(--acc);font-weight:800;opacity:0;animation:fadeup .4s ease .95s forwards}
.cf{position:fixed;top:-12px;width:9px;height:14px;border-radius:2px;z-index:10;animation:fall linear forwards}@keyframes fall{to{transform:translateY(110vh) rotate(720deg)}}


.step[hidden]{display:none}.langs{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:6px}
.langs button{background:var(--card);color:var(--ink);border:1px solid var(--line);text-align:left;font-weight:600;padding:11px 14px;display:flex;justify-content:space-between}
.langs button{align-items:center;gap:10px;transition:border-color .15s,box-shadow .15s,transform .1s}.langs button:hover{border-color:var(--acc);color:var(--acc)}.langs button:active{transform:scale(.98)}
.langs button span{color:var(--ink3);font-weight:500;font-size:12.5px;margin-left:auto}.langs button.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc),0 6px 18px rgba(91,91,214,.14);color:var(--ink)}
.flag{width:26px;height:17px;flex:none;border-radius:3px}
.ailang[hidden]{display:none!important}.ailang{display:flex;align-items:center;gap:12px;margin-top:16px;padding:12px 14px;border-radius:14px;background:linear-gradient(135deg,var(--acc2),var(--acc2b));border:1px solid var(--acc3);animation:up .25s ease}
.ailang .aii{width:34px;height:34px;flex:none;border-radius:10px;background:var(--acc);display:grid;place-items:center}.ailang .aii svg{width:20px;height:20px;fill:var(--card)}
.ailang b{display:block;font-size:14.5px}.ailang small{display:block;color:var(--ink2);font-size:12.5px;line-height:1.4;margin-top:2px}.ailang button{margin-left:auto;flex:none}
@keyframes up{from{opacity:0;transform:translateY(6px)}}
.seg{display:inline-flex;background:var(--soft);border-radius:10px;padding:3px;gap:3px}.seg button{background:none;color:var(--ink2);padding:7px 14px}.seg button.on{background:var(--card);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.08)}
.fl{margin:14px 0 6px;font-size:13px;color:var(--ink3);font-weight:600}.nav{display:flex;justify-content:space-between;align-items:center;margin-top:22px}
button:disabled{opacity:.45;cursor:default}.thhint{margin:14px 0 0;font-size:13px;color:var(--ink3);min-height:18px;transition:color .3s}

:root{--bg:#f4f3ef;--card:#fff;--ink:#16181d;--ink2:#4b505a;--ink3:#8a909a;--line:#e5e3dc;--soft:#efeee9;--acc:#5b5bd6;--acc2:#ecebff;--acc2b:#eaf4ff;--acc3:#dcdafb;--okb:#f1faf4;--okl:#bfe3cd;--blob:.55}
[data-theme=dark]{--bg:#0f1115;--card:#171a21;--ink:#e8e9ee;--ink2:#a9adb8;--ink3:#7d828d;--line:#2a2e38;--soft:#1e222b;--acc:#7b7cf5;--acc2:#262842;--acc2b:#1d2a3a;--acc3:#3a3c66;--okb:#15281e;--okl:#24543a;--blob:.22}
body{transition:background .35s,color .35s}.box,.opt,.langs button,.vg button,input,select,.seg{transition:background .35s,border-color .35s,color .35s}
input,select{background:var(--card);color:var(--ink)}
.bg i{opacity:var(--blob)!important}
.themes{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:8px}
.themes button{background:var(--card);color:var(--ink);border:1px solid var(--line);padding:10px;display:flex;flex-direction:column;gap:10px;align-items:stretch;opacity:0;animation:cardin .45s cubic-bezier(.2,1.2,.3,1) forwards}
.themes button:hover{border-color:var(--acc);transform:translateY(-2px)}.themes button.on{border-color:var(--acc);box-shadow:0 0 0 2px var(--acc)}
.themes .pv{height:96px;border-radius:10px;position:relative;overflow:hidden;border:1px solid rgba(0,0,0,.08)}
.pv.l{background:#f4f3ef}.pv.d{background:#0f1115}.pv.a{background:linear-gradient(115deg,#f4f3ef 50%,#0f1115 50%)}
.pv i{position:absolute;border-radius:6px}.pv .sb{left:0;top:0;bottom:0;width:22%}.pv.l .sb{background:#e9e7e0}.pv.d .sb{background:#171a21}.pv.a .sb{background:#e9e7e0}
.pv .b1{left:30%;top:18%;width:46%;height:16%}.pv .b2{left:44%;top:44%;width:46%;height:16%}.pv .b3{left:30%;top:70%;width:34%;height:14%}
.pv.l .b1,.pv.l .b3{background:#fff}.pv.d .b1,.pv.d .b3{background:#232733}.pv.a .b1{background:#fff}.pv.a .b3{background:#232733}.pv .b2{background:#6d5ff5}
.pv .b1,.pv .b2,.pv .b3{animation:bub 3.2s ease-in-out infinite}.pv .b2{animation-delay:.4s}.pv .b3{animation-delay:.8s}
@keyframes bub{0%,10%{transform:scale(.6);opacity:0}20%,80%{transform:none;opacity:1}100%{opacity:0}}
.themes b{font-size:14px;display:flex;align-items:center;gap:8px}.themes b svg{width:18px;height:18px}
.reveal{position:fixed;inset:0;z-index:20;pointer-events:none;animation:reveal .7s cubic-bezier(.6,0,.2,1) forwards}@keyframes reveal{from{clip-path:circle(0 at var(--x) var(--y))}to{clip-path:circle(150vmax at var(--x) var(--y))}}
</style></head><body><div class="bg"><i></i><i></i><i></i></div>
<div class="splash" id="splash"><div><div class="lg"></div><div class="wm" id="wm"></div><div class="tg">memory for any AI</div></div></div>
<div class="box"><div class="brand"><i></i>Mnemai<div class="dots"><b class="on"></b><b></b><b></b><b></b></div></div>
<div class="step" id="s0" data-noi18n><h1>Light or dark?</h1><p>Pick how Mnemai looks. You can change it any time.</p><div class="themes" id="themes">
<button data-th="light"><div class="pv l"><i class="sb"></i><i class="b1"></i><i class="b2"></i><i class="b3"></i></div><b><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>Light</b></button>
<button data-th="dark"><div class="pv d"><i class="sb"></i><i class="b1"></i><i class="b2"></i><i class="b3"></i></div><b><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z"/></svg>Dark</b></button>
<button data-th="system"><div class="pv a"><i class="sb"></i><i class="b1"></i><i class="b2"></i><i class="b3"></i></div><b><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17a8.5 8.5 0 000-17z" fill="currentColor" stroke="none"/></svg>Like Windows</b></button></div>
<p class="thhint" id="thhint">Click a card to see how it looks.</p><div class="nav"><span></span><button id="n0">Continue</button></div></div>
<div class="step" id="s1" data-noi18n hidden><h1>Choose your language</h1><p>Mnemai will speak with you in this language.</p><div class="langs" id="langs"></div>
<div class="ailang" id="ailang" hidden><div class="aii"><svg viewBox="0 0 24 24"><path d="M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4z"/><path d="M18 15l.8 2 2 .8-2 .8L18 21l-.8-2.4-2-.8 2-.8z"/></svg></div><div><b id="ait"></b><small id="ais"></small></div></div>
<div class="nav"><button class="l" id="b1">Back</button><button id="n1" disabled>Continue</button></div></div>
<div class="step" id="s2" hidden><div class="hello" id="hello"><span class="hand">👋</span><span id="hellot"></span></div><h1>Как к тебе обращаться?</h1><p>Так ИИ будут звать тебя в ответах. Можно поменять в настройках.</p>
<div class="fl">Имя</div><input id="nm" placeholder="например, Иван" style="width:100%;box-sizing:border-box">
<div class="fl">Пол</div><div class="seg" id="gd"><button data-v="m">Мужской</button><button data-v="f">Женский</button><button data-v="" class="on">Не указывать</button></div>
<div class="fl">Обращение</div><div class="seg" id="ad"><button data-v="ty" class="on">На ты</button><button data-v="vy">На вы</button></div>
<div class="nav"><button class="l" id="b2">Назад</button><button id="n2">Дальше</button></div></div>
<div class="step" id="s3" hidden><div class="memart"><svg viewBox="0 0 150 76"><rect x="88" y="26" width="56" height="44" rx="8" fill="#ecebff" stroke="#5b5bd6" stroke-width="2"/><path d="M88 34h22l5-6h29" fill="none" stroke="#5b5bd6" stroke-width="2"/>
<g class="f"><rect x="18" y="8" width="20" height="24" rx="3" fill="#fff" stroke="#8a909a" stroke-width="1.5"/><path d="M22 15h12M22 20h12M22 25h8" stroke="#b9b8c9" stroke-width="1.5"/></g>
<g class="f f2"><rect x="30" y="2" width="20" height="24" rx="3" fill="#fff" stroke="#8a909a" stroke-width="1.5"/><path d="M34 9h12M34 14h12M34 19h8" stroke="#b9b8c9" stroke-width="1.5"/></g>
<g class="f f3"><rect x="10" y="16" width="20" height="24" rx="3" fill="#fff" stroke="#8a909a" stroke-width="1.5"/><path d="M14 23h12M14 28h12M14 33h8" stroke="#b9b8c9" stroke-width="1.5"/></g></svg></div><h1>Память о тебе для любого ИИ</h1><p>Она живёт у тебя на компьютере обычными файлами и учится ровно настолько, насколько ты разрешишь.</p>
<details class="opt" id="pxbox"><summary>Подключаюсь через прокси или VPN</summary><div class="h">Через него пойдут все разговоры с ИИ, поиск и скачивание моделей.</div>
<div class="vg" id="vg"></div><div id="vpnr"></div>
<div class="h" style="margin-top:12px">Или впиши вручную:</div>
<div class="px"><select id="pxt"><option value="http">HTTP</option><option value="socks5">SOCKS5</option></select><input id="pxh" placeholder="адрес, например 127.0.0.1"><input id="pxp" placeholder="порт"></div>
<div class="px2"><input id="pxu" placeholder="логин, если нужен" autocomplete="off"><input id="pxw" type="password" placeholder="пароль" autocomplete="new-password"></div>
<div class="row" style="margin-top:10px"><button class="l" id="pxc">Проверить</button></div><div id="pxr"></div></details>
<div class="opt"><b>Завести свою память</b><div class="h">Папка, где будет лежать память: обычные файлы, которые можно открыть в любом редакторе.</div>
<div class="row"><input id="p"><button class="l" id="pick">Выбрать…</button><button id="mk">Создать</button></div></div>
<div id="err"></div><div class="nav"><button class="l" id="b3">Назад</button><span></span></div></div></div>
<script>
const STAR='M0,-1L.294,-.405L.951,-.309L.476,.155L.588,.809L0,.5L-.588,.809L-.476,.155L-.951,-.309L-.294,-.405Z';
const FLAGS={
 ru:'<rect width="30" height="20" fill="#fff"/><rect y="6.67" width="30" height="6.67" fill="#0039A6"/><rect y="13.33" width="30" height="6.67" fill="#D52B1E"/>',
 en:'<rect width="30" height="20" fill="#012169"/><path d="M0,0L30,20M30,0L0,20" stroke="#fff" stroke-width="4"/><path d="M0,0L30,20M30,0L0,20" stroke="#C8102E" stroke-width="1.6"/><path d="M15,0V20M0,10H30" stroke="#fff" stroke-width="6"/><path d="M15,0V20M0,10H30" stroke="#C8102E" stroke-width="3.4"/>',
 zh:`<rect width="30" height="20" fill="#DE2910"/><path d="${STAR}" fill="#FFDE00" transform="translate(6,6) scale(3)"/><path d="${STAR}" fill="#FFDE00" transform="translate(11,2.5) scale(1)"/><path d="${STAR}" fill="#FFDE00" transform="translate(13,5) scale(1)"/><path d="${STAR}" fill="#FFDE00" transform="translate(13,8.5) scale(1)"/><path d="${STAR}" fill="#FFDE00" transform="translate(11,11) scale(1)"/>`,
 es:'<rect width="30" height="20" fill="#AA151B"/><rect y="5" width="30" height="10" fill="#F1BF00"/>',
 hi:'<rect width="30" height="20" fill="#fff"/><rect width="30" height="6.67" fill="#FF9933"/><rect y="13.33" width="30" height="6.67" fill="#138808"/><circle cx="15" cy="10" r="2.6" fill="none" stroke="#000080" stroke-width=".8"/><circle cx="15" cy="10" r=".6" fill="#000080"/>',
 ar:'<rect width="30" height="20" fill="#006C35"/><path d="M8,7.5c2-1.5 4,1 6-.5s3,1 5,0 3,1 3.5,.2" fill="none" stroke="#fff" stroke-width="1.1" stroke-linecap="round"/><path d="M8,12.5H21.5l1.5-1" fill="none" stroke="#fff" stroke-width="1.1" stroke-linecap="round"/>',
 pt:'<rect width="30" height="20" fill="#FF0000"/><rect width="12" height="20" fill="#006600"/><circle cx="12" cy="10" r="3.6" fill="#FFCC00"/><circle cx="12" cy="10" r="2.2" fill="#FF0000"/><rect x="11" y="8.6" width="2" height="2.8" rx=".4" fill="#fff"/>',
 fr:'<rect width="30" height="20" fill="#fff"/><rect width="10" height="20" fill="#0055A4"/><rect x="20" width="10" height="20" fill="#EF4135"/>',
 de:'<rect width="30" height="20" fill="#000"/><rect y="6.67" width="30" height="6.67" fill="#DD0000"/><rect y="13.33" width="30" height="6.67" fill="#FFCE00"/>',
 ja:'<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="6" fill="#BC002D"/>'};
const flag=k=>`<svg class="flag" viewBox="0 0 30 20"><clipPath id="fc${k}"><rect width="30" height="20" rx="3"/></clipPath><g clip-path="url(#fc${k})">${FLAGS[k]||''}</g><rect width="30" height="20" rx="3" fill="none" stroke="rgba(0,0,0,.12)"/></svg>`;
// what the AI will do, said in the language just chosen
const AI_LANG={ru:['ИИ будет отвечать тебе на русском','Даже если напишешь на другом языке. Поменять можно в любой момент кнопкой языка справа вверху.','Дальше'],
 en:['The AI will answer you in English','Even if you write in another language. Change it anytime with the language button at the top right.','Continue'],
 zh:['AI 将用中文回答你','即使你用其他语言书写也是如此。可随时通过右上角的语言按钮更改。','继续'],
 es:['La IA te responderá en español','Aunque escribas en otro idioma. Puedes cambiarlo cuando quieras con el botón de idioma arriba a la derecha.','Continuar'],
 hi:['AI आपको हिन्दी में जवाब देगा','भले ही आप किसी और भाषा में लिखें। ऊपर दाईं ओर भाषा बटन से इसे कभी भी बदल सकते हैं।','आगे'],
 pt:['A IA vai responder em português','Mesmo que você escreva em outro idioma. Dá para mudar a qualquer momento no botão de idioma no canto superior direito.','Continuar'],
 fr:['L’IA te répondra en français','Même si tu écris dans une autre langue. Tu peux la changer à tout moment avec le bouton de langue en haut à droite.','Continuer'],
 de:['Die KI antwortet dir auf Deutsch','Auch wenn du in einer anderen Sprache schreibst. Ändern kannst du das jederzeit über die Sprachtaste oben rechts.','Weiter'],
 ja:['AI は日本語で答えます','別の言語で書いても同じです。右上の言語ボタンでいつでも変更できます。','次へ']};
const LANGS=[['ru','Русский'],['en','English'],['zh','中文'],['es','Español'],['hi','हिन्दी'],['pt','Português'],['fr','Français'],['de','Deutsch'],['ja','日本語']];
const DICT=__SETUP_I18N__;let LANG='en';const ORIG=new Map();
function trAll(){const d=DICT[LANG]||{};document.documentElement.dir='ltr';document.documentElement.lang=LANG;
  const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT|NodeFilter.SHOW_ELEMENT,{acceptNode:n=>n.nodeType===1&&n.matches('[data-noi18n],script,style')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
  let n;while((n=w.nextNode())){if(n.nodeType===3){if(!ORIG.has(n))ORIG.set(n,n.nodeValue);const o=ORIG.get(n),k=o.trim();if(k)n.nodeValue=d[k]?o.replace(k,d[k]):o}
    else if(n.placeholder){if(!ORIG.has(n))ORIG.set(n,n.placeholder);n.placeholder=d[ORIG.get(n)]||ORIG.get(n)}}}
const T=t=>(DICT[LANG]||{})[t]||t;
let CUR=0,THEME='system';const show=i=>{for(const k of [0,1,2,3]){const e=document.getElementById('s'+k);e.hidden=k!==i;e.classList.toggle('back',i<CUR)}CUR=i;
  document.querySelectorAll('.dots b').forEach((b,k)=>b.classList.toggle('on',k<=i));if(i===2)hello()};
const sysDark=()=>matchMedia('(prefers-color-scheme: dark)').matches;
const paint=m=>{document.documentElement.dataset.theme=(m==='dark'||(m==='system'&&sysDark()))?'dark':'light'};paint('system');
document.querySelectorAll('[data-th]').forEach((b,i)=>{b.style.animationDelay=(2.15+i*.08)+'s';b.onclick=e=>{THEME=b.dataset.th;
  document.querySelectorAll('[data-th]').forEach(x=>x.classList.toggle('on',x===b));
  const was=document.documentElement.dataset.theme,next=(THEME==='dark'||(THEME==='system'&&sysDark()))?'dark':'light';
  if(was!==next){const r=document.createElement('div');r.className='reveal';r.style.setProperty('--x',e.clientX+'px');r.style.setProperty('--y',e.clientY+'px');
    r.style.background=next==='dark'?'#0f1115':'#f4f3ef';document.body.appendChild(r);setTimeout(()=>{paint(THEME)},420);setTimeout(()=>r.remove(),760)}
  document.getElementById('thhint').textContent=THEME==='system'?'Follows Windows: light by day, dark at night if Windows does so.':'This is how it will look. Try another or continue.'}});
document.querySelectorAll('[data-th]').forEach(b=>b.classList.toggle('on',b.dataset.th===THEME));
document.getElementById('n0').onclick=()=>show(1);
document.getElementById('wm').innerHTML='Mnemai'.split('').map((c,i)=>`<span style="animation-delay:${.55+i*.08}s">${c}</span>`).join('');
setTimeout(()=>{const sp=document.getElementById('splash');if(sp)sp.remove()},2500);
document.querySelectorAll('#langs button').forEach((b,i)=>b.style.animationDelay=(.05+i*.05)+'s');
const HI={ru:'Приятно познакомиться',en:'Nice to meet you',zh:'很高兴认识你',es:'Encantado de conocerte',hi:'आपसे मिलकर खुशी हुई',ar:'تشرفت بمعرفتك',pt:'Prazer em conhecer',fr:'Ravi de te rencontrer',de:'Schön, dich kennenzulernen',ja:'はじめまして'};
function hello(){const n=(document.getElementById('nm').value||'').trim();document.getElementById('hellot').innerHTML=(HI[LANG]||HI.en)+(n?`, <span class="nm">${n.replace(/[<>&]/g,'')}</span>!`:'!')}
document.getElementById('langs').innerHTML=LANGS.map(([k,n])=>`<button data-l="${k}">${flag(k)}${n}<span>${k.toUpperCase()}</span></button>`).join('');
document.getElementById('nm').addEventListener('input',()=>hello());
document.querySelectorAll('[data-l]').forEach(b=>{b.onclick=()=>{LANG=b.dataset.l;trAll();
  document.querySelectorAll('[data-l]').forEach(x=>x.classList.toggle('on',x===b));const a=AI_LANG[LANG],box=document.getElementById('ailang');
  document.getElementById('ait').textContent=a[0];document.getElementById('ais').textContent=a[1];document.getElementById('n1').textContent=a[2];document.getElementById('n1').disabled=false;
  document.getElementById('b1').textContent=({ru:'Назад',en:'Back',zh:'返回',es:'Atrás',hi:'पीछे',ar:'رجوع',pt:'Voltar',fr:'Retour',de:'Zurück',ja:'戻る'})[LANG]||'Back';
  box.hidden=false;box.style.animation='none';void box.offsetWidth;box.style.animation=''};b.ondblclick=()=>show(2)});
document.getElementById('n1').onclick=()=>show(2);
const pick=id=>document.querySelectorAll('#'+id+' button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#'+id+' button').forEach(x=>x.classList.toggle('on',x===b))});
pick('gd');pick('ad');
const val=id=>(document.querySelector('#'+id+' .on')||{}).dataset.v||'';
const prefs=()=>({theme:THEME,lang:LANG,gender:val('gd'),name:document.getElementById('nm').value.trim(),address:val('ad')||'ty'});
document.getElementById('b2').onclick=()=>show(1);
document.getElementById('b1').onclick=()=>show(0);document.getElementById('n2').onclick=()=>show(3);document.getElementById('b3').onclick=()=>show(2);
const err=e=>document.getElementById('err').textContent=e;
window.addEventListener('pywebviewready',async()=>{document.getElementById('p').value=await pywebview.api.default_path()});
document.getElementById('pick').onclick=async()=>{const p=await pywebview.api.pick('folder');if(p)document.getElementById('p').value=p};
const g=id=>document.getElementById(id).value.trim();
const px=()=>{if(!document.getElementById('pxbox').open||!g('pxh'))return '';return g('pxt')+'://'+(g('pxu')?encodeURIComponent(g('pxu'))+'@':'')+g('pxh')+(g('pxp')?':'+g('pxp'):'')};
const VPN=[['Hiddify','proxy',[12334,12335]],['Happ','proxy',[10808,10809]],['v2rayN','proxy',[10808,10809]],['Clash','proxy',[7890,7897]],['NekoRay','proxy',[2080,2081]],['OpenVPN','tunnel'],['WireGuard','tunnel'],['AmneziaVPN','tunnel']];
let SCAN=null;const scan=f=>{if(f||!SCAN)SCAN=(window.pywebview?pywebview.api.proxy_detect():Promise.resolve({proxies:[],tunnels:[]})).catch(()=>({proxies:[],tunnels:[]}));return SCAN};
const match=(d,[n,k,ports])=>k==='tunnel'?((d.tunnels||[]).some(t=>t.toLowerCase().startsWith(n.toLowerCase().slice(0,6)))?{tunnel:1}:null):((d.proxies||[]).find(p=>p.name.toLowerCase().startsWith(n.toLowerCase().slice(0,4)))||(d.proxies||[]).find(p=>(ports||[]).includes(p.port))||null);
const vg=document.getElementById('vg');vg.innerHTML=VPN.map(a=>`<button data-vn="${a[0]}"><i></i>${a[0]}<small>${a[1]==='tunnel'?T('на всю систему'):T('через прокси')}</small></button>`).join('');
const markV=d=>vg.querySelectorAll('[data-vn]').forEach(b=>{const a=VPN.find(x=>x[0]===b.dataset.vn);b.classList.toggle('live',!!match(d,a))});
document.getElementById('pxbox').addEventListener('toggle',e=>{if(e.target.open)scan().then(markV)});
vg.querySelectorAll('[data-vn]').forEach(b=>b.onclick=async()=>{const a=VPN.find(x=>x[0]===b.dataset.vn),r=document.getElementById('vpnr');vg.querySelectorAll('button').forEach(x=>x.classList.toggle('sel',x===b));
  r.innerHTML=`<div class="vr"><div>${T('Ищу')} ${a[0]}…</div></div>`;const d=await scan(true);markV(d);const hit=match(d,a);
  if(hit&&hit.tunnel){['pxh','pxp','pxu','pxw'].forEach(id=>document.getElementById(id).value='');r.innerHTML=`<div class="vr sys"><i></i><div><b>${a[0]}</b> <small>${T('работает на всю систему — Mnemai пойдёт через него сама. Поля оставь пустыми.')}</small></div></div>`;return}
  if(hit){const u=new URL(hit.url.replace('socks5:','http:'));document.getElementById('pxt').value=hit.url.split(':')[0];document.getElementById('pxh').value=u.hostname;document.getElementById('pxp').value=u.port;
    r.innerHTML=`<div class="vr ok"><i></i><div><b>${a[0]}</b> <small>${T('подключён')}: ${hit.url.replace('://',' · ')} · ${hit.ms} ms</small></div></div>`;return}
  r.innerHTML=`<div class="vr"><div>${a[1]==='tunnel'?a[0]+' '+T('не запущен. Открой его и подключись — Mnemai пойдёт через него сама.'):a[0]+' '+T('не найден. Открой')+' '+a[0]+', '+T('включи подключение и нажми эту кнопку ещё раз.')}</div></div>`});
document.getElementById('pxc').onclick=async()=>{const r=document.getElementById('pxr');if(!g('pxh')){r.textContent=T('Укажи адрес прокси');return}r.textContent=T('проверяю…');
  const x=await pywebview.api.proxy_check(px(),document.getElementById('pxw').value);r.textContent=x.ok?T('Работает')+' · '+x.via+' · '+x.ms+' ms':T('Не работает')+': '+x.error;r.style.color=x.ok?'#1f8a4c':'#c2413d'};
const PARTY={ru:['достижение · первое','Память создана','Теперь любой ИИ будет знать тебя'],en:['achievement · first','Memory created','Now any AI will know you']};
function party(){const t=PARTY[LANG]||PARTY.en,d=document.createElement('div');d.className='party';
  d.innerHTML=`<div><div style="position:relative;display:grid;place-items:center"><div class="md">🧠</div></div><div class="t1">${t[0]}</div><div class="t2">${t[1]}</div><div class="t3">${t[2]}</div><div style="text-align:center"><span class="xp">+10 XP</span></div></div>`;
  document.body.appendChild(d);const C=['#6d5ff5','#4fb6ff','#ffcf4a','#ff7ab6','#3ccf91'];
  for(let i=0;i<90;i++){const c=document.createElement('i');c.className='cf';c.style.left=Math.random()*100+'vw';c.style.background=C[i%C.length];
    c.style.animationDuration=(1.6+Math.random()*1.6)+'s';c.style.animationDelay=(Math.random()*.6)+'s';c.style.transform=`rotate(${Math.random()*360}deg)`;document.body.appendChild(c)}}
document.getElementById('mk').onclick=async()=>{const b=document.getElementById('mk');b.disabled=true;err('');
  const r=await pywebview.api.create(document.getElementById('p').value,px(),document.getElementById('pxw').value,prefs());if(r){err(r);b.disabled=false}else party()};

</script></body></html>"""


def windows_dark() -> bool:
    """The system's colour: dark or light (the first screen opens in it before the owner picks)."""
    return OS.system_dark()


MISSING_TEXT = {
    "ru": (
        "Не нашла папку памяти",
        "Память была здесь:",
        "Если ты перенёс или переименовал папку, укажи, где она сейчас. Если это внешний диск — подключи его и "
        "нажми «Проверить снова». Ничего не удалено: Mnemai не трогала папку.",
        "Указать, где она",
        "Проверить снова",
        "Начать новую память",
    ),
    "en": (
        "Your memory folder is missing",
        "It used to be here:",
        "If you moved or renamed the folder, show where it is now. If it is on an external drive, plug it in and "
        "press «Check again». Nothing was deleted: Mnemai did not touch the folder.",
        "Show where it is",
        "Check again",
        "Start new memory",
    ),
}


def start_screen(cfg: dict) -> str:
    """What the window opens with: the memory ("vault"), the first screen ("setup") or, when the memory folder of the
    last run is gone, a screen that says so ("missing") — never a silent fresh start."""
    path = cfg.get("vault")
    if path and Path(path).exists():
        return "vault"
    return "missing" if path and not cfg.get("demo") else "setup"


def missing_html(path: str, lang: str = "ru") -> str:
    """The memory folder from the last run is gone (moved, renamed, a drive not plugged in): say so, never start over
    silently."""
    import html as _h

    t = MISSING_TEXT["ru" if (lang or "ru") == "ru" else "en"]
    return f"""<!doctype html><html lang="{'ru' if lang == 'ru' else 'en'}"><head><meta charset="utf-8"><style>
body{{margin:0;font:15px/1.55 "Segoe UI",system-ui,sans-serif;background:#f4f3ef;color:#1d1d1f;display:grid;place-items:center;min-height:100vh}}
@media (prefers-color-scheme:dark){{body{{background:#0f1115;color:#e9e9ee}}.box{{background:#171a21!important;border-color:#2a2f3a!important}}code{{background:#232834!important}}}}
.box{{width:560px;background:#fff;border:1px solid #e5e3dc;border-radius:18px;padding:32px 36px}}h1{{font-size:22px;margin:0 0 12px}}
p{{margin:0 0 14px;opacity:.85}}code{{display:block;padding:8px 10px;border-radius:8px;background:#f1efe9;word-break:break-all;margin:0 0 14px}}
.row{{display:flex;gap:10px;flex-wrap:wrap}}button{{font:inherit;border-radius:10px;padding:9px 16px;border:1px solid #d9d6cc;background:transparent;color:inherit;cursor:pointer}}
button.main{{background:#5b5bd6;border-color:#5b5bd6;color:#fff}}#err{{color:#c2413d;min-height:1.4em;margin-top:10px}}</style></head>
<body><div class="box"><h1>{_h.escape(t[0])}</h1><p>{_h.escape(t[1])}</p><code id="path">{_h.escape(path)}</code><p>{_h.escape(t[2])}</p>
<div class="row"><button class="main" id="pick">{_h.escape(t[3])}</button><button id="again">{_h.escape(t[4])}</button><button id="anew">{_h.escape(t[5])}</button></div><div id="err"></div></div>
<script>
const err=e=>document.getElementById('err').textContent=e||'';
document.getElementById('pick').onclick=async()=>{{const p=await pywebview.api.pick('folder');if(p)err(await pywebview.api.open_existing(p))}};
document.getElementById('again').onclick=async()=>err(await pywebview.api.open_existing(document.getElementById('path').textContent));
document.getElementById('anew').onclick=()=>pywebview.api.start_new();
</script></body></html>"""


SETUP_RU = {  # the first two screens are in English for everyone, but in Russian on a Russian Windows
    "<h1>Light or dark?</h1>": "<h1>Светлая или тёмная?</h1>",
    "Pick how Mnemai looks. You can change it any time.": "Выбери, как будет выглядеть Mnemai. Поменять можно в любой момент.",
    "</svg>Light</b>": "</svg>Светлая</b>",
    "</svg>Dark</b>": "</svg>Тёмная</b>",
    "</svg>Like Windows</b>": "</svg>Как в Windows</b>",
    "Click a card to see how it looks.": "Нажми на карточку — покажу, как это будет выглядеть.",
    '<button id="n0">Continue</button>': '<button id="n0">Дальше</button>',
    "<h1>Choose your language</h1>": "<h1>Выбери язык</h1>",
    "Mnemai will speak with you in this language.": "На этом языке Mnemai будет говорить с тобой.",
    '<button class="l" id="b1">Back</button>': '<button class="l" id="b1">Назад</button>',
    '<button id="n1" disabled>Continue</button>': '<button id="n1" disabled>Дальше</button>',
    "'Follows Windows: light by day, dark at night if Windows does so.'": "'Как в Windows: днём светлая, ночью тёмная, если так настроена Windows.'",
    "'This is how it will look. Try another or continue.'": "'Так это будет выглядеть. Попробуй другую или жми «Дальше».'",
}


def windows_lang() -> str:
    """ "ru" when the system speaks Russian, else "en"."""
    return OS.ui_lang()


def setup_html(lang: str | None = None) -> str:
    """The first screen with its own texts translated into every language (from ui/i18n/*.json)."""
    texts = set(t.strip() for t in re.findall(r">([^<>]*[А-Яа-яЁё][^<>]*)<", SETUP_HTML))
    texts |= set(re.findall(r'placeholder="([^"]*[А-Яа-яЁё][^"]*)"', SETUP_HTML))
    texts |= set(re.findall(r"T\('([^']+)'\)", SETUP_HTML))
    d = {}
    folder = Path(__file__).parent / "ui" / "i18n"
    for f in folder.glob("*.json") if folder.exists() else []:
        try:
            exact = json.loads(f.read_text(encoding="utf-8")).get("exact", {})
        except ValueError:
            continue
        d[f.stem] = {t: exact[t] for t in texts if t in exact}
    html = SETUP_HTML.replace("__SETUP_I18N__", json.dumps(d, ensure_ascii=False))
    if lang == "ru":  # English by default; Russian only when asked for
        for en, ru in SETUP_RU.items():
            html = html.replace(en, ru)
    return OS.os_words(html)


# ---------------------------------------------------------------- the app


class App:
    def __init__(self, hidden: bool):
        self.hidden = hidden
        self.window = None
        self.tray = None
        self.server = None
        self.learner = None
        self.vault: Vault | None = None
        self.port = 0
        self.quitting = False

    # -- js api (window.pywebview.api.*)
    class Api:
        def __init__(self, app: "App"):
            self._app = app

        def close_choice(self, choice: str, remember: bool = False):
            self._app.close_choice(choice, bool(remember))

        def default_path(self) -> str:
            from . import upgrade

            return str(upgrade.free_memory_path())

        def pick(self, kind: str = "folder"):
            dlg = webview.FOLDER_DIALOG if kind == "folder" else webview.OPEN_DIALOG
            r = self._app.window.create_file_dialog(dlg)
            return r[0] if r else ""

        def open_existing(self, path: str):
            """«Указать, где она»: an existing memory folder opens as is; anything else says why not."""
            try:
                v = Vault(Path(path).expanduser())
                if not v.root.exists():
                    return "Этой папки нет. Проверь, подключён ли диск." if self._lang() == "ru" else "No such folder."
                if not v.exists():
                    return (
                        "Здесь нет памяти Mnemai: нет файла «70 Memory/Profile.md». Выбери папку, где лежат «70 Memory» и «.mnema»."
                        if self._lang() == "ru"
                        else "There is no Mnemai memory here: «70 Memory/Profile.md» is missing."
                    )
                self._app.open_vault(v, demo=False)
            except Exception as e:
                return f"Не получилось: {e}"

        def start_new(self):
            self._app.window.load_html(setup_html())

        def _lang(self) -> str:
            return load_config().get("lang") or "en"

        def proxy_detect(self):
            from . import vpn_detect

            return vpn_detect.detect()

        def proxy_check(self, url: str, password: str = ""):
            from . import net

            return net.check(url, password or "")

        def _prefs(self, v: Vault, prefs: dict | None):
            if not prefs:
                return
            from .agent import profile as P

            patch = {
                "lang": prefs.get("lang") or "en",
                "gender": prefs.get("gender") or "",
                "owner_name": (prefs.get("name") or "")[:60],
                "ui_theme": prefs.get("theme") if prefs.get("theme") in ("light", "dark", "system") else "",
            }
            if prefs.get("address") in ("ty", "vy"):
                patch["simple"] = {"address": prefs["address"]}
            P.save(v, patch)

        def _proxy(self, v: Vault, url: str, password: str):
            if url:
                from . import net

                net.save(v, url, password or "")

        def create(self, path: str, proxy: str = "", password: str = "", prefs: dict | None = None):
            if not (path or "").strip():
                return "Укажи папку для памяти — или нажми «Выбрать…»."
            try:
                p = Path(path.strip()).expanduser()
                if not p.is_absolute():
                    example = "C:\\Users\\Имя\\Mnemai" if OS.IS_WIN else "~/Mnemai"
                    return f"Нужен полный путь к папке, например {example} — или нажми «Выбрать…»."
                if p.drive and not Path(p.drive + "\\").exists():
                    return f"Диска {p.drive} нет на компьютере. Выбери другую папку."
                bad = set('<>"|?*') & set(str(p)[len(p.drive) :]) if OS.IS_WIN else set()
                if bad:
                    return "В пути есть знаки, которые Windows не разрешает в именах папок: " + " ".join(sorted(bad))
                if OS.IS_WIN and any(
                    x.upper().split(".")[0]
                    in (
                        "CON",
                        "PRN",
                        "AUX",
                        "NUL",
                        *(f"COM{i}" for i in range(1, 10)),
                        *(f"LPT{i}" for i in range(1, 10)),
                    )
                    for x in p.parts[1:]
                ):
                    return "Такое имя папки Windows не разрешает (CON, NUL, COM1…). Выбери другое."
                from . import upgrade

                if upgrade.old_layout(p):  # the first build's memory: left as it is, new one beside it
                    p = p.with_name(p.name + " Memory")
                if upgrade.is_app_dir(p) or any(upgrade.is_app_dir(x) for x in p.parents):
                    p = upgrade.free_memory_path()  # never inside a program folder: an update replaces it
                if p.exists() and any(p.iterdir()) and not Vault(p).exists() and not (p / ".mnema").exists():
                    p = p / "Mnemai"  # never spill memory files into a non-empty folder
                v = Vault(p)
                fresh = not v.exists()
                init_vault(v)
                self._proxy(v, proxy, password)
                self._prefs(v, prefs)
                if fresh:  # a new memory starts switched off: the tour offers to turn it on
                    from .agent import profile as P

                    P.save(v, {"memory_on": False})
                self._app.open_vault(v, demo=False, delay=2.4)  # the celebration on the first screen plays first
            except PermissionError:
                return "Нет прав записывать в эту папку. Выбери другую — например, в «Документах»."
            except OSError as e:
                return f"Не получилось создать папку: {e.strerror or e}. Выбери другую."
            except Exception as e:
                return f"Не получилось: {e}"

        def demo(self, proxy: str = "", password: str = "", prefs: dict | None = None):
            try:
                p = HOME / "demo"
                v = Vault(p)
                if not v.exists():
                    make_demo(v)
                self._proxy(v, proxy, password)
                self._prefs(v, prefs)
                self._app.open_vault(v, demo=True)
            except Exception as e:
                return f"Не получилось: {e}"

    def open_vault(self, vault: Vault, demo: bool, delay: float = 0.3) -> None:
        cfg = load_config()
        cfg.update(vault=str(vault.root), demo=demo)
        if not demo:  # the memories this computer knows: the settings switch between them
            mine = str(vault.root)
            cfg["vaults"] = [mine] + [p for p in cfg.get("vaults") or [] if Path(p) != Path(mine)][:11]
        save_config(cfg)
        self.start_server(vault)
        # let the JS call that asked for it return first, then navigate
        t = threading.Timer(delay, lambda: self.window.load_url(self.url()))
        t.daemon = True
        t.start()

    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start_server(self, vault: Vault) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.learner:
            self.learner.stop()
        self.vault = vault
        self.port = free_port()
        api.APP_HOOKS.update(
            show=self.show,
            autostart=self.autostart_api,
            info=self.info,
            switch=self.switch,
            vaults=self.vaults_api,
            vault_open=self.vault_open_api,
            vault_forget=self.vault_forget_api,
            vault_rename=self.vault_rename_api,
            close_pref=self.close_pref_api,
            quit=self.quit_api,
        )
        self.server = api.make_server(vault, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True, name="mnema-api").start()
        self.learner = engine.Learner(vault)
        from . import crypt

        if crypt.locked(vault.root):  # encrypted, the password is asked in the window: learning waits for it
            api.APP_HOOKS["unlocked"] = lambda: None if self.learner.is_alive() else self.learner.start()
        else:
            self.learner.start()
        # sync (Google Drive, Dropbox, a folder, a station) is hidden from the settings since 22.10.2026 and doesn't
        # run in the background: the code stays in sync.py, the section can come back
        cfg = load_config()
        cfg["port"] = self.port
        try:  # the language of the screen shown if this folder is ever missing at start
            from .agent import profile as P

            cfg["lang"] = P.load(vault).get("lang") or "en"
        except Exception:
            pass
        save_config(cfg)
        self.refresh_tray()

    # -- hooks for the UI
    def info(self, _=None) -> dict:
        cfg = load_config()
        return {
            "version": __version__,
            "port": self.port,
            "vault": str(self.vault.root) if self.vault else "",
            "demo": bool(cfg.get("demo")),
            "autostart": autostart_enabled(),
            "desktop": True,
            "on_close": cfg.get("on_close", "ask"),
        }

    def autostart_api(self, body=None) -> dict:
        set_autostart(bool((body or {}).get("on")))
        self.refresh_tray()
        return self.info()

    def vaults_api(self, _=None) -> dict:
        """The memories this computer knows, the open one first."""
        cfg = load_config()
        cur = str(self.vault.root) if self.vault else ""
        known = cfg.get("vaults") or []
        if cur and not cfg.get("demo") and cur not in known:
            known = [cur] + known
        return {
            "current": "" if cfg.get("demo") else cur,
            "list": [
                {
                    "path": p,
                    "name": (cfg.get("names") or {}).get(p) or Path(p).name or p,
                    "exists": Vault(Path(p)).exists(),
                }
                for p in known
            ],
        }

    def vault_open_api(self, body=None) -> dict:
        p = Path(str((body or {}).get("path") or "")).expanduser()
        v = Vault(p)
        if not v.exists():
            return {"error": "Здесь нет памяти Mnemai: нет файла «70 Memory/Profile.md»."}
        self.open_vault(v, demo=False, delay=0.4)
        return {"ok": True}

    def vault_rename_api(self, body=None) -> dict:
        """The name a memory is shown with in the settings; the folder itself keeps its name."""
        b = body or {}
        cfg = load_config()
        names = cfg.get("names") or {}
        path, name = str(b.get("path") or ""), str(b.get("name") or "").strip()[:60]
        if name:
            names[path] = name
        else:
            names.pop(path, None)
        cfg["names"] = names
        save_config(cfg)
        return {"ok": True, **self.vaults_api()}

    def vault_forget_api(self, body=None) -> dict:
        """Take a memory off the list; with delete — its folder goes to the Recycle Bin. The open one is closed first:
        the window moves to the next memory on the list (or to the first screen) and then the folder goes."""
        from . import osapi

        b = body or {}
        p = Path(str(b.get("path") or ""))
        if self.vault and p.resolve() == self.vault.root.resolve():
            if not b.get("delete"):
                return {"error": "Это открытая память."}
            nxt = next((x for x in load_config().get("vaults") or [] if Path(x) != p and Vault(Path(x)).exists()), None)
            threading.Thread(target=self._close_and_delete, args=(p, nxt), daemon=True).start()
            return {"ok": True, "closing": True, "next": nxt or ""}
        if b.get("delete") and p.exists():
            if not Vault(p).exists():
                return {"error": "Здесь нет памяти Mnemai — папку не трогаю."}
            if not osapi.to_trash(p):
                return {"error": "Не получилось переместить папку в корзину. Закрой файлы из неё и повтори."}
        cfg = load_config()
        cfg["vaults"] = [x for x in cfg.get("vaults") or [] if Path(x) != p]
        save_config(cfg)
        return {"ok": True, **self.vaults_api()}

    def _close_and_delete(self, p: Path, nxt: str | None) -> None:
        """The open memory is being deleted: let the answer reach the window, close the memory, wipe the folder."""
        from . import osapi

        time.sleep(0.4)
        cfg = load_config()
        cfg["vaults"] = [x for x in cfg.get("vaults") or [] if Path(x) != p]
        (cfg.get("names") or {}).pop(str(p), None)
        if not nxt:
            cfg.update(vault="", demo=False)
        save_config(cfg)
        old = self.learner
        if nxt:
            self.open_vault(Vault(Path(nxt)), demo=False, delay=0.1)  # stops this memory's server and learning
        else:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
            if old:
                old.stop()
            self.learner = None
            self.vault = None
            self.window.load_html(setup_html())
        if old and old.is_alive():
            old.join(timeout=15)
        for _ in range(20):  # a file still held by a finishing write: try again for a while
            if osapi.to_trash(p):
                return
            time.sleep(1)
        cfg = load_config()  # couldn't: the memory comes back on the list, deleting it again shows the reason
        cfg["vaults"] = (cfg.get("vaults") or []) + [str(p)]
        save_config(cfg)

    def switch(self, _=None) -> dict:
        """Back to the first screen: create own memory instead of the demo."""
        self.window.load_html(setup_html())
        return {"ok": True}

    # -- window
    def show(self, _=None) -> dict:
        if self.window:
            self.window.show()
            self.window.restore()
        return {"ok": True}

    def on_closing(self):
        """The window's ×: ask "в трей или закрыть" (with "запомнить"), or do what was remembered."""
        if self.quitting:
            return True
        pref = load_config().get("on_close", "ask")
        if pref == "quit":
            threading.Thread(target=self.quit, daemon=True).start()
            return False
        if pref == "tray" and self.tray:
            self.window.hide()
            return False

        def ask():
            try:
                r = self.window.evaluate_js("typeof mnemaAskClose==='function' ? (mnemaAskClose(), 'ok') : 'no'")
            except Exception:
                r = "no"
            if r != "ok":  # first-launch screen: nothing to keep alive
                self.quit()

        threading.Thread(target=ask, daemon=True).start()
        return False

    def close_choice(self, choice: str, remember: bool) -> None:
        if remember and choice in ("tray", "quit"):
            cfg = load_config()
            cfg["on_close"] = choice
            save_config(cfg)
        if choice == "tray" and self.tray:
            self.window.hide()
        elif choice == "tray":  # no tray on this desktop: hiding would lose the window
            threading.Thread(target=self.quit, daemon=True).start()
        elif choice == "quit":
            threading.Thread(target=self.quit, daemon=True).start()

    def close_pref_api(self, body=None) -> dict:
        v = str((body or {}).get("value", "ask"))
        if v in ("ask", "tray", "quit"):
            cfg = load_config()
            cfg["on_close"] = v
            save_config(cfg)
        return self.info()

    # -- tray
    def queue_size(self) -> int:
        try:
            return len(Ledger(self.vault).queue()) if self.vault else 0
        except Exception:
            return 0

    def paused(self) -> bool:
        return bool(self.vault and S.load(self.vault)["paused"])

    def toggle_pause(self, *_):
        s = S.load(self.vault)
        s["paused"] = not s["paused"]
        S.save(self.vault, s)
        self.refresh_tray()

    def learn_now(self, *_):
        if self.vault:
            from .api_learn import start_run

            start_run(self.vault)

    def toggle_autostart(self, *_):
        set_autostart(not autostart_enabled())
        self.refresh_tray()

    def quit_api(self):  # graceful stop for restarts: the tray icon goes away with the process
        t = threading.Timer(0.3, self.quit)
        t.daemon = True
        t.start()
        return {"ok": True}

    def quit(self, *_):
        self.quitting = True
        if self.learner:
            self.learner.stop()
        if self.tray:
            self.tray.stop()
        if self.window:
            self.window.destroy()

    def refresh_tray(self):
        if not self.tray:
            return
        self.tray.title = f"Mnemai — {'на паузе' if self.paused() else 'учится'}"
        self.tray.update_menu()

    def open_proxy(self, *_):
        self.show()
        if self.window:
            self.window.evaluate_js("location.hash==='#settings/net'?go('settings','net'):location.hash='settings/net'")

    def menu_items(self) -> list:
        """(label, action, enabled, checked) — the same menu for every tray."""

        def has(*_):
            from . import crypt

            return bool(self.vault) and not crypt.locked(self.vault.root)

        return [
            ("Открыть Mnemai", lambda *_: self.show(), None, None),
            ("Учиться сейчас", self.learn_now, has, None),
            (lambda *_: "Продолжить обучение" if self.paused() else "Пауза обучения", self.toggle_pause, has, None),
            ("Прокси…", self.open_proxy, has, None),
            (AUTOSTART_LABEL, self.toggle_autostart, None, lambda *_: autostart_enabled()),
            None,
            ("Выход", self.quit, None, None),
        ]

    def build_tray(self):
        """pystray on Windows and macOS. On Linux the window runs on Qt, so the tray is Qt's own (qt_tray, started
        with the window). A tray that can't start never stops the program: closing the window then quits."""
        if OS.IS_LINUX:
            return
        try:
            import pystray

            items = []
            for it in self.menu_items():
                if it is None:
                    items.append(pystray.Menu.SEPARATOR)
                    continue
                label, act, enabled, checked = it
                kw = {"default": True} if label == "Открыть Mnemai" else {}
                if enabled:
                    kw["enabled"] = enabled
                if checked:
                    kw["checked"] = checked
                items.append(pystray.MenuItem(label, act, **kw))
            self.tray = pystray.Icon(APP, icon_image(64), "Mnemai", pystray.Menu(*items))
            self.tray.run_detached()
        except Exception:
            self.tray = None
            return
        self._tray_ready()

    def qt_tray(self):
        """Linux: the tray icon through Qt, created in Qt's own thread once the window is up."""
        try:
            from qtpy.QtCore import QObject, Signal
            from qtpy.QtGui import QAction, QIcon, QPixmap
            from qtpy.QtWidgets import QApplication, QMenu, QSystemTrayIcon
        except Exception:
            return

        def make():
            app = QApplication.instance()
            if not app or not QSystemTrayIcon.isSystemTrayAvailable():
                return
            import io

            buf = io.BytesIO()
            icon_image(64).save(buf, "PNG")
            pm = QPixmap()
            pm.loadFromData(buf.getvalue(), "PNG")
            tray = QSystemTrayIcon(QIcon(pm), app)
            menu = QMenu()
            acts = []
            for it in self.menu_items():
                if it is None:
                    menu.addSeparator()
                    continue
                label, act, enabled, checked = it
                a = QAction(label() if callable(label) else label, menu)
                a.triggered.connect(lambda _=False, f=act: threading.Thread(target=f, daemon=True).start())
                if checked:
                    a.setCheckable(True)
                menu.addAction(a)
                acts.append((a, label, enabled, checked))

            def refresh():
                for a, label, enabled, checked in acts:
                    if callable(label):
                        a.setText(label())
                    if enabled:
                        a.setEnabled(bool(enabled()))
                    if checked:
                        a.setChecked(bool(checked()))

            menu.aboutToShow.connect(refresh)
            tray.setContextMenu(menu)
            tray.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
            tray.setToolTip("Mnemai")
            tray.show()
            self.tray = _QtTray(tray)

        class _Gui(QObject):  # a call from this thread runs in Qt's thread through a queued signal
            go = Signal()

            def run(self):
                make()

        app = QApplication.instance()
        if not app:
            return
        gui = _Gui()
        gui.moveToThread(app.thread())
        gui.go.connect(gui.run)
        self._qt_keep = gui
        gui.go.emit()
        self._tray_ready()

    def _tray_ready(self):
        from . import scribe_cloud

        def tray_note(text):  # meetings tell the owner where and how long, even when hidden
            try:
                self.tray.notify(text, "Mnemai")
            except Exception:
                pass

        scribe_cloud.NOTIFY[0] = tray_note

        def tick():
            while not self.quitting:
                self.refresh_tray()
                threading.Event().wait(60)

        threading.Thread(target=tick, daemon=True).start()

    def run(self):
        cfg = load_config()
        from . import upgrade

        if cfg.get("vault") and upgrade.old_layout(Path(cfg["vault"])):  # the first build's settings: clean start
            upgrade.put_aside_old_settings(HOME)
            cfg = load_config()
        try:  # подключения прежней Mnema в Claude и Cursor переходят на имя mnemai
            from .cli import migrate_mcp

            migrate_mcp()
        except Exception:  # noqa: BLE001 — чужие файлы настроек не должны мешать запуску
            pass
        vault = Vault(cfg["vault"]) if start_screen(cfg) == "vault" else None
        missing = start_screen(cfg) == "missing"
        if vault:
            self.start_server(vault)  # server first: the window opens straight on it
        self.window = webview.create_window(
            APP,
            url=self.url() if vault else None,
            html=None if vault else (missing_html(cfg["vault"], cfg.get("lang", "en")) if missing else setup_html()),
            width=1240,
            height=860,
            min_size=(900, 600),
            hidden=self.hidden,
            js_api=App.Api(self),
            background_color=("#0f1115" if windows_dark() else "#f4f3ef"),
            text_select=True,
        )
        self.window.events.closing += self.on_closing
        self.build_tray()
        from .updater import Updater

        updater = Updater(HOME, load_config)
        updater.start()
        if os.environ.get("MNEMA_DEBUG_PORT"):  # developer check of the real window (localhost only)
            webview.settings["REMOTE_DEBUGGING_PORT"] = int(os.environ["MNEMA_DEBUG_PORT"])
        kw = {"gui": "qt", "func": self.qt_tray} if OS.IS_LINUX else {}
        webview.start(private_mode=False, storage_path=str(HOME / "webview"), **kw)
        try:
            updater.on_exit()
        except Exception:  # updating is optional; a failed helper must not break normal exit
            pass


def _crash_log() -> None:
    """Any failure — Python error in any thread or a hard crash — is written to app.log with the time."""
    import faulthandler
    import threading
    import traceback

    HOME.mkdir(parents=True, exist_ok=True)
    f = (HOME / "app.log").open("a", encoding="utf-8", buffering=1)

    def write(kind, exc_type, exc, tb):
        f.write(
            f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {kind}\n"
            + "".join(traceback.format_exception(exc_type, exc, tb))
        )

    sys.excepthook = lambda t, e, tb: write("ошибка", t, e, tb)
    threading.excepthook = lambda a: write(
        f"ошибка в потоке {a.thread.name if a.thread else ''}", a.exc_type, a.exc_value, a.exc_traceback
    )
    faulthandler.enable(file=f, all_threads=True)  # hard crashes (native code) too
    _crash_log.file = f


WEBVIEW2 = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def webview2_installed() -> bool:
    """The Microsoft component that draws the window. Windows 11 has it, a clean Windows 10 may not."""
    import winreg

    keys = [
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2}"),
        (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2}"),
    ]
    for root, path in keys:
        try:
            with winreg.OpenKey(root, path) as k:
                v = str(winreg.QueryValueEx(k, "pv")[0])
                if v and v != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def ensure_webview2() -> bool:
    """Install WebView2 with Microsoft's own installer shipped inside Mnemai (needs the internet once).
    macOS and Linux draw the window with their own engine."""
    if not OS.IS_WIN or webview2_installed():
        return True
    import subprocess

    setup = (
        Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1] / "vendor"))
        / "webview2"
        / "MicrosoftEdgeWebview2Setup.exe"
    )
    if not setup.exists():
        setup = Path(__file__).resolve().parents[1] / "vendor" / "webview2" / "MicrosoftEdgeWebview2Setup.exe"
    OS.message(
        "Для окна Mnemai нужен компонент Microsoft WebView2. Сейчас он установится — это один раз, "
        "около минуты, нужен интернет.\n\nMnema needs the Microsoft WebView2 component. "
        "It will be installed now, once."
    )
    try:
        subprocess.run([str(setup), "/silent", "/install"], timeout=600)
    except Exception:
        pass
    if webview2_installed():
        return True
    OS.message(
        "Не получилось поставить Microsoft WebView2. Проверь интернет или поставь его вручную: "
        "https://go.microsoft.com/fwlink/p/?LinkId=2124703\n\nCould not install Microsoft WebView2.",
        error=True,
    )
    return False


def login_path() -> None:
    """A program opened from the Dock or the app menu gets a bare PATH (/usr/bin:/bin): Claude Code, Node and Ollama
    installed by the owner are not on it. Take the PATH his login shell sets up, plus the usual places."""
    if OS.IS_WIN:
        return
    import subprocess

    parts = os.environ.get("PATH", "").split(os.pathsep)
    try:
        shell = os.environ.get("SHELL") or "/bin/zsh"
        r = subprocess.run([shell, "-ilc", "printf %s \"$PATH\""], capture_output=True, text=True, timeout=8)
        parts += r.stdout.strip().splitlines()[-1].split(os.pathsep) if r.stdout.strip() else []
    except Exception:
        pass
    home = Path.home()
    parts += [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        str(home / ".local" / "bin"),
        str(home / ".claude" / "local"),
        str(home / ".npm-global" / "bin"),
        str(home / ".bun" / "bin"),
        str(home / ".volta" / "bin"),
    ]
    seen, out = set(), []
    for x in parts:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    os.environ["PATH"] = os.pathsep.join(out)


class _QtTray:
    """What the rest of the app asks of a tray (title, menu refresh, a note, stop), over Qt's QSystemTrayIcon."""

    def __init__(self, icon):
        self.icon = icon

    @property
    def title(self):
        return self.icon.toolTip()

    @title.setter
    def title(self, v):
        self.icon.setToolTip(v)

    def update_menu(self):
        pass  # refreshed every time the menu opens

    def notify(self, text, title="Mnemai"):
        self.icon.showMessage(title, text)

    def stop(self):
        self.icon.hide()


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] not in ("--hidden",):
        from .cli import main as cli_main  # Mnemai.exe init/serve/... works like the CLI

        return cli_main(argv)
    if already_running():
        return
    purge_dead_tray_icons()
    _crash_log()
    login_path()
    if not ensure_webview2():
        return
    if OS.IS_WIN:
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Mnemai.Desktop")
        except Exception:
            pass
    try:
        App(hidden="--hidden" in argv).run()
    except Exception:
        import traceback

        HOME.mkdir(parents=True, exist_ok=True)
        with (HOME / "app.log").open("a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
        OS.message(f"Mnemai не смогла запуститься. Подробности записаны в файл:\n{HOME / 'app.log'}", error=True)
    finally:
        _exit_now()


def _exit_now() -> None:
    """The window is gone: stop what Mnemai started (the local model, the VPN engine) and leave. Python would otherwise
    wait for every helper thread — a library's or a request still running — and the program hangs without a window
    (seen on macOS: Mnemai stays in the Dock and «Завершить» does nothing)."""
    import atexit

    try:
        atexit._run_exitfuncs()
    except Exception:
        pass
    try:
        f = getattr(_crash_log, "file", None)
        if f:
            f.flush()
    except Exception:
        pass
    os._exit(0)


if __name__ == "__main__":
    main()
