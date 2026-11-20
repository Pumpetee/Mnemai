"""Контрактные тесты /api/ping и /api/app/* после переноса в декларативный роутер (Часть 2).

Проверяется, что перенесённые маршруты сохранили те же пути, коды, JSON и тексты ошибок, что были в
ручных ветках api.py: хуки окна вызываются так же (с сырым телом), без окна — те же ответы «не desktop»,
токен по-прежнему обязателен. Дополнительно: APP_HOOKS — единый для desktop и роутера, а net-маршруты
зовут те же функции приложения, что и js_api (vpn_detect.detect, net.check).
"""

import contextlib
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())  # never touch the real home
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema import api  # noqa: E402
from mnema import http_router  # noqa: E402
from mnema.http_router import APP_HOOKS, GET_ROUTES, POST_ROUTES  # noqa: E402
from mnema.memory import init_vault, token  # noqa: E402
from mnema.vault import Vault  # noqa: E402


def _info():
    return {
        "version": "2.5.7",
        "port": 7461,
        "vault": "",
        "demo": False,
        "autostart": False,
        "desktop": True,
        "on_close": "ask",
    }


class TestAppContract(unittest.TestCase):
    """/api/ping и /api/app/*: контракт путей, кодов и ключей ответа через настоящий сервер."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        cls.v = Vault(cls.dir)
        init_vault(cls.v)
        cls.srv = api.make_server(cls.v, 0)
        cls.port = cls.srv.server_address[1]
        cls.srv.server_close()
        cls.srv = api.make_server(cls.v, cls.port)  # повторный вызов: APP_PORT = cls.port
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tok = token(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def setUp(self):
        self.saved = dict(APP_HOOKS)
        APP_HOOKS.clear()

    def tearDown(self):
        APP_HOOKS.clear()
        APP_HOOKS.update(self.saved)

    def req(self, path, data=None, with_token=True):
        r = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            method="POST" if data is not None else "GET",
            data=json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None,
        )
        if with_token:
            r.add_header("X-Mnema-Token", self.tok)
        r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            with contextlib.closing(e):
                return e.code, json.loads(e.read().decode("utf-8"))

    def test_hooks_dict_is_shared_between_api_and_router(self):
        """desktop заполняет api.APP_HOOKS — роутер видит те же хуки (ViewModel единый)."""
        self.assertIs(api.APP_HOOKS, http_router.APP_HOOKS)

    def test_migrated_routes_have_schemas(self):
        """У каждого перенесённого маршрута есть request_schema и response_schema."""
        migrated = [r for r in (*GET_ROUTES, *POST_ROUTES) if r.path == "/api/ping" or r.path.startswith("/api/app/")]
        self.assertEqual(len(migrated), 20)  # 9 GET + 1 GET-фолбэк, 9 POST + 1 POST-фолбэк
        for r in migrated:
            self.assertIsNotNone(r.request_schema, r.path)
            self.assertIsNotNone(r.response_schema, r.path)

    def test_ping_contract(self):
        code, body = self.req("/api/ping")
        self.assertEqual(code, 200)
        self.assertEqual(sorted(body), ["lang", "ok", "version"])
        self.assertTrue(body["ok"])

    def test_selftest_contract(self):
        code, body = self.req("/api/app/selftest")
        self.assertEqual(code, 200)
        self.assertEqual(sorted(body), ["crypt", "ocr", "telegram"])

    def test_app_get_hooks(self):
        APP_HOOKS.update(
            show=lambda: {"ok": True},
            switch=lambda: {"ok": True},
            quit=lambda: {"ok": True},
            info=lambda: _info(),
            vaults=lambda: {"current": "", "list": []},
            update=lambda: {"desktop": False, "current": "2.5.7", "available": False},
        )
        self.assertEqual(self.req("/api/app/show")[1], {"ok": True})
        self.assertEqual(self.req("/api/app/switch")[1], {"ok": True})
        self.assertEqual(self.req("/api/app/quit")[1], {"ok": True})
        self.assertEqual(self.req("/api/app/info")[1], _info())
        self.assertEqual(self.req("/api/app/vaults")[1], {"current": "", "list": []})
        self.assertEqual(self.req("/api/app/update")[1], {"desktop": False, "current": "2.5.7", "available": False})

    def test_app_get_fallback_without_desktop(self):
        for path in ("/api/app/info", "/api/app/show", "/api/app/update"):
            code, body = self.req(path)
            self.assertEqual(code, 200)
            self.assertEqual(body, {"desktop": False, "port": self.port})

    def test_app_get_unknown_name(self):
        for path in ("/api/app/nope", "/api/app/"):
            code, body = self.req(path)
            self.assertEqual(code, 200)
            self.assertEqual(body, {"desktop": False, "port": self.port})

    def test_app_post_hooks_receive_raw_body(self):
        for name in ("autostart", "close_pref", "vault_open", "vault_forget", "vault_rename", "update_do"):
            got = {}
            APP_HOOKS[name] = lambda body, got=got: got.update(body=body) or _info()
            sent = {"path": "/tmp/x", "name": "и", "on": "off", "value": 7, "delete": 0, "action": "check"}
            code, _ = self.req(f"/api/app/{name}", sent)
            self.assertEqual(code, 200, name)
            self.assertEqual(got["body"], sent, name)  # сырое тело, без приведений

    def test_app_post_fallback_without_desktop(self):
        for path in ("/api/app/autostart", "/api/app/close_pref", "/api/app/update_do"):
            code, body = self.req(path, {"on": True})
            self.assertEqual(code, 200)
            self.assertEqual(body, {"desktop": False})
        code, body = self.req("/api/app/nope", {})
        self.assertEqual(code, 200)
        self.assertEqual(body, {"desktop": False})

    def test_app_routes_require_token(self):
        for path in ("/api/ping", "/api/app/selftest", "/api/app/info"):
            code, body = self.req(path, with_token=False)
            self.assertEqual(code, 401)
            self.assertEqual(body, {"error": "нужен токен"})
        code, body = self.req("/api/app/autostart", {"on": True}, with_token=False)
        self.assertEqual(code, 401)
        self.assertEqual(body, {"error": "нужен токен"})

    def test_net_detect_calls_same_app_function_as_js_api(self):
        """HTTP /api/net/detect зовёт ту же функцию vpn_detect.detect(), что и js_api proxy_detect."""
        from mnema.http_router import dispatch

        with mock.patch("mnema.vpn_detect.detect", return_value={"ok": "sentinel"}) as m:
            code, body = dispatch(self.v, "GET", "/api/net/detect", {}, None)
        self.assertEqual(code, 200)
        self.assertEqual(body, {"ok": "sentinel"})
        m.assert_called_once_with()

    def test_net_check_calls_same_app_function_as_js_api(self):
        """HTTP /api/net/check зовёт ту же функцию net.check(), что и js_api proxy_check."""
        from mnema.http_router import dispatch

        with mock.patch("mnema.http_router.net.check", return_value={"ok": "sentinel"}) as m:
            code, body = dispatch(self.v, "POST", "/api/net/check", {}, {"proxy": "http://x", "password": "p"})
        self.assertEqual(code, 200)
        self.assertEqual(body, {"ok": "sentinel"})
        m.assert_called_once_with("http://x", "p")


class TestFirstRunContract(unittest.TestCase):
    """Первый запуск через HTTP (headless): default_path, create, demo, open_existing и ключевые сценарии."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        cls.v = Vault(cls.dir)
        init_vault(cls.v)
        cls.srv = api.make_server(cls.v, 0)
        cls.port = cls.srv.server_address[1]
        cls.srv.server_close()
        cls.srv = api.make_server(cls.v, cls.port)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tok = token(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def setUp(self):
        self.saved = dict(APP_HOOKS)
        APP_HOOKS.clear()

    def tearDown(self):
        APP_HOOKS.clear()
        APP_HOOKS.update(self.saved)

    def req(self, path, data=None):
        r = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            method="POST" if data is not None else "GET",
            data=json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None,
        )
        r.add_header("X-Mnema-Token", self.tok)
        r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=20) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            with contextlib.closing(e):
                return e.code, json.loads(e.read().decode("utf-8"))

    def test_default_path(self):
        code, body = self.req("/api/app/default_path")
        self.assertEqual(code, 200)
        self.assertTrue(str(body["path"]))

    def test_create_empty_path_says_so(self):
        code, body = self.req("/api/app/create", {"path": ""})
        self.assertEqual(code, 400)
        self.assertEqual(body, {"error": "Укажи папку для памяти — или нажми «Выбрать…»."})

    def test_create_relative_path_is_rejected(self):
        code, body = self.req("/api/app/create", {"path": "память"})
        self.assertEqual(code, 400)
        self.assertIn("Нужен полный путь к папке", body["error"])

    def test_create_then_open_existing(self):
        mem = Path(tempfile.mkdtemp()) / "память"
        code, body = self.req("/api/app/create", {"path": str(mem)})
        self.assertEqual(code, 200)
        self.assertEqual(body["ok"], True)
        self.assertEqual(body["path"], str(mem))
        self.assertTrue((mem / "70 Memory" / "Profile.md").is_file())
        code, body = self.req("/api/app/open_existing", {"path": str(mem), "lang": "ru"})
        self.assertEqual(code, 200)
        self.assertEqual(body, {"ok": True, "path": str(mem)})
        shutil.rmtree(mem.parent, ignore_errors=True)

    def test_open_existing_missing_folder(self):
        code, body = self.req("/api/app/open_existing", {"path": "/нет/такой/папки", "lang": "ru"})
        self.assertEqual(code, 400)
        self.assertEqual(body, {"error": "Этой папки нет. Проверь, подключён ли диск."})

    def test_demo_creates_vault(self):
        code, body = self.req("/api/app/demo", {})
        self.assertEqual(code, 200)
        self.assertEqual(body["ok"], True)
        self.assertIn("demo", body["path"])

    def test_headless_scenario(self):
        """Ключевые сценарии без окна: ping → создание памяти → чат-поверхность → запись → журнал."""
        code, body = self.req("/api/ping")
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        mem = Path(tempfile.mkdtemp()) / "память"
        code, body = self.req("/api/app/create", {"path": str(mem)})
        self.assertEqual(body["ok"], True)
        code, body = self.req("/api/session/new", {})
        self.assertEqual(code, 200)
        self.assertIn("id", body)
        code, body = self.req("/api/chats")
        self.assertEqual(code, 200)
        self.assertIn("chats", body)
        code, body = self.req("/api/remember", {"fact": "headless-факт для журнала"})
        self.assertEqual(code, 200)
        code, journal = self.req("/api/journal")
        self.assertEqual(code, 200)
        self.assertTrue(any("headless-факт" in str(e) for e in journal))
        shutil.rmtree(mem.parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
