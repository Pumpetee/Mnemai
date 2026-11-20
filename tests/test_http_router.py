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

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())  # never touch the real home
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema.api import make_server  # noqa: E402
from mnema.http_router import dispatch  # noqa: E402
from mnema.http_schemas import RequestSchema, ResponseSchema, SchemaError, fields  # noqa: E402
from mnema.memory import init_vault, token  # noqa: E402
from mnema.vault import Vault  # noqa: E402


class TestSchemas(unittest.TestCase):
    """Валидация входов: приведение типов, значения по умолчанию, единый формат ошибок."""

    def test_coercions_and_defaults(self):
        schema = RequestSchema(
            body=fields(text=("str", ""), limit=("int", 100), web=("bool", None), economy=("bool", True))
        )
        # значения по умолчанию, когда полей нет
        self.assertEqual(schema.validate(body={}), {"text": "", "limit": 100, "web": None, "economy": True})
        # приведение типов: int из строки, bool по правилам Python (как в прежних ручных ветках)
        out = schema.validate(body={"text": 7, "limit": "42", "web": 0, "economy": "off"})
        self.assertEqual(out, {"text": "7", "limit": 42, "web": False, "economy": True})
        # явный null: bool(None) = False, str(None) = "None" — 1:1 со старым поведением
        out = schema.validate(body={"text": None, "web": None})
        self.assertEqual(out["text"], "None")
        self.assertEqual(out["web"], False)

    def test_invalid_int_propagates(self):
        schema = RequestSchema(query=fields(limit=("int", 100)))
        with self.assertRaises(ValueError):
            schema.validate({"limit": "abc"})

    def test_response_schema_check(self):
        ok_schema = ResponseSchema("object", ("ok",))
        ok_schema.check({"ok": True})
        with self.assertRaises(SchemaError):
            ok_schema.check({})
        with self.assertRaises(SchemaError):
            ok_schema.check([])
        arr = ResponseSchema("array")
        arr.check([])
        with self.assertRaises(SchemaError):
            arr.check({"ok": True})

    def test_declared_responses_match_contract(self):
        """Ответы маршрутов с объявленными схемами проходят check() на живых данных."""
        from mnema.http_router import GET_ROUTES, POST_ROUTES

        d = Path(tempfile.mkdtemp())
        try:
            v = Vault(d)
            init_vault(v)
            cases = [
                (dispatch(v, "GET", "/api/now", {}), ResponseSchema("object", ("text",))),
                (dispatch(v, "GET", "/api/journal", {}), ResponseSchema("array")),
                (dispatch(v, "GET", "/api/clients", {}), ResponseSchema("array")),
                (dispatch(v, "POST", "/api/ach/seen", {}), ResponseSchema("object", ("ok",))),
            ]
            for (code, payload), schema in cases:
                self.assertEqual(code, 200)
                schema.check(payload)
            declared = [r for r in (*GET_ROUTES, *POST_ROUTES) if r.response_schema]
            self.assertGreaterEqual(len(declared), 10)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_old_call_points_still_work(self):
        """api_chat.get/post и api_learn.get/post делегируют роутеру и не ломают старые вызовы."""
        from mnema import api_chat, api_learn

        d = Path(tempfile.mkdtemp())
        try:
            v = Vault(d)
            init_vault(v)
            code, body = api_chat.get(v, "/api/models", {})
            self.assertEqual(code, 200)
            self.assertIn("providers", body)
            code, body = api_chat.post(v, "/api/settings/reset", {})
            self.assertEqual(code, 200)
            self.assertTrue(body["ok"])
            code, body = api_learn.post(v, "/api/learn/review_all", {})
            self.assertEqual(code, 200)
            self.assertIn("done", body)
            code, body = api_learn.get(v, "/api/learn/items", {"view": "queue"})
            self.assertEqual(code, 200)
            self.assertIn("items", body)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TestRouter(unittest.TestCase):
    """Ключевые маршруты и единый формат ошибок через настоящий сервер."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        cls.v = Vault(cls.dir)
        init_vault(cls.v)
        cls.srv = make_server(cls.v, 0)
        cls.port = cls.srv.server_address[1]
        cls.srv.server_close()
        cls.srv = make_server(cls.v, cls.port)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tok = token(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def req(self, path, data=None):
        r = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            method="POST" if data is not None else "GET",
            data=json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None,
        )
        r.add_header("X-Mnema-Token", self.tok)
        r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            with contextlib.closing(
                e
            ):  # HTTPError — тоже файлоподобный ответ: закрываем, чтобы не было ResourceWarning
                return e.code, json.loads(e.read().decode("utf-8"))

    def test_ping_ok(self):
        code, body = self.req("/api/ping")
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        self.assertIn("version", body)

    def test_now_and_journal(self):
        code, body = self.req("/api/now")
        self.assertEqual(code, 200)
        self.assertIn("text", body)
        code, body = self.req("/api/journal")
        self.assertEqual(code, 200)
        self.assertIsInstance(body, list)

    def test_remember_undo_roundtrip(self):
        code, body = self.req("/api/remember", {"fact": "факт из теста роутера"})
        self.assertEqual(code, 200)
        self.assertIn("факт из теста роутера", self.v.read_raw("00 Inbox/Inbox.md"))
        code, body = self.req("/api/undo", {"id": body["id"]})
        self.assertEqual(code, 200)
        self.assertNotIn("факт из теста роутера", self.v.read_raw("00 Inbox/Inbox.md"))

    def test_unified_error_format(self):
        # 404: единый формат {"error": ...}
        code, body = self.req("/api/no-such-route")
        self.assertEqual(code, 404)
        self.assertEqual(body, {"error": "нет такого пути"})
        # 400: неверный входной параметр оборачивается в тот же формат
        code, body = self.req("/api/journal?limit=abc")
        self.assertEqual(code, 400)
        self.assertIn("error", body)
        # 400: известная ошибка обработчика
        code, body = self.req("/api/vpn", {"action": "неизвестное"})
        self.assertEqual(code, 400)
        self.assertEqual(body, {"error": "неизвестное действие"})

    def test_clients_roundtrip(self):
        code, clients = self.req("/api/clients")
        self.assertEqual(code, 200)
        gem = next(c for c in clients if c["id"] == "gemini")
        gem["enabled"] = False
        self.assertEqual(self.req("/api/clients", clients)[0], 200)
        self.assertEqual(self.req("/api/clients", [])[0], 400)
        gem["enabled"] = True
        self.req("/api/clients", clients)

    def test_prefix_routes(self):
        # неизвестное под-действие префиксного маршрута /api/local/ → 404, как раньше
        self.assertEqual(self.req("/api/local/nonexistent", {})[0], 404)
        # /api/sync/ отдаёт публичное состояние даже при неизвестном под-действии
        code, body = self.req("/api/sync/nonexistent", {})
        self.assertEqual(code, 200)
        self.assertIn("targets", body)


if __name__ == "__main__":
    unittest.main()
