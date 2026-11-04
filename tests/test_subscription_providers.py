"""Offline contract checks for subscription-backed providers; no credentials or network calls."""

import base64
import io
import queue
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema.chat import codex_auth as CA  # noqa: E402
from mnema.chat import codex_server as CS  # noqa: E402
from mnema.chat import model_rank  # noqa: E402
from mnema.chat import providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


class SubscriptionProviders(unittest.TestCase):
    def setUp(self):
        self.vault = Vault(Path(tempfile.mkdtemp()))
        init_vault(self.vault)

    def test_provider_metadata_and_order(self):
        self.assertFalse(PR.PROVIDERS["codex"]["key"])
        self.assertTrue(PR.PROVIDERS["opencode_go"]["key"])
        self.assertTrue(PR.PROVIDERS["codex"]["subscription"])
        self.assertTrue(PR.PROVIDERS["opencode_go"]["subscription"])
        self.assertEqual(model_rank.rank("codex", ["gpt-5", "gpt-5-mini"]), ["gpt-5", "gpt-5-mini"])
        self.assertEqual(model_rank.rank("opencode_go", ["go/model-b", "go/model-a"]), ["go/model-b", "go/model-a"])

    def test_opencode_go_catalog_uses_subscription_key_and_session_headers(self):
        seen = {}

        def catalog(url, headers):
            seen.update(url=url, headers=headers)
            return {"data": [{"id": "go/model-a"}, {"id": "go/model-b"}]}

        with (
            mock.patch.object(PR.secrets_store, "put"),
            mock.patch.object(PR.secrets_store, "get", return_value="test-subscription-key"),
            mock.patch.object(PR, "_get", side_effect=catalog),
        ):
            PR.save(self.vault, "opencode_go", key="test-subscription-key")
            models = PR.fetch_models(self.vault, "opencode_go")
        self.assertEqual(models, ["go/model-a", "go/model-b"])
        self.assertEqual(seen["url"], "https://opencode.ai/inference/go/v1/models")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer test-subscription-key")
        self.assertEqual(seen["headers"]["x-opencode-session"], "mnemai-model-catalog")
        self.assertIn("Mnemai/", seen["headers"]["User-Agent"])

    def test_opencode_go_answer_uses_chat_completions_and_stable_chat_session(self):
        seen = {}

        def events(req):
            seen["url"] = req.full_url
            seen["headers"] = req.header_items()
            seen["body"] = json.loads(req.data.decode("utf-8"))
            yield {"choices": [{"delta": {"content": "Привет"}}]}
            yield {"_done": True}

        with (
            mock.patch.object(PR, "key_of", return_value="test-subscription-key"),
            mock.patch.object(PR, "_sse", side_effect=lambda req, **kw: events(req)),
        ):
            answer = "".join(
                PR._stream_raw(
                    self.vault,
                    "opencode_go",
                    "kimi-k3",
                    "",
                    [{"role": "user", "text": "Привет"}],
                    meta={"chat": "chat-session-123"},
                )
            )
        headers = {key.lower(): value for key, value in seen["headers"]}
        self.assertEqual(answer, "Привет")
        self.assertEqual(seen["url"], "https://opencode.ai/inference/go/openai/v1/chat/completions")
        self.assertEqual(headers["authorization"], "Bearer test-subscription-key")
        self.assertEqual(headers["x-opencode-session"], "chat-session-123")
        self.assertEqual(seen["body"]["model"], "kimi-k3")

    def test_codex_history_is_plain_text_and_marks_unsupported_files(self):
        text = CS._plain_history(
            "Пиши кратко",
            [
                {"role": "user", "text": "Привет", "files": [{"kind": "image", "path": "C:/private/photo.png"}]},
                {"role": "assistant", "text": "Здравствуйте"},
            ],
        )
        self.assertIn("Инструкции Mnemai", text)
        self.assertIn("Пользователь:\nПривет", text)
        self.assertIn("[Вложение недоступно провайдеру Codex: photo.png]", text)
        self.assertNotIn("C:/private", text)

    def test_chatgpt_oauth_callback_requires_scope_state_and_same_identity(self):
        pending = {
            "state": "expected-state",
            "nonce": "expected-nonce",
            "verifier": "pkce-verifier",
            "redirect_uri": "http://127.0.0.1:43210/auth/callback",
            "client_id": "",
            "subject": "",
            "host_id": "urn:uuid:host",
        }
        token_result = {
            "access_token": "access-test",
            "refresh_token": "refresh-test",
            "id_token": "id-test",
            "scope": "openid email offline_access resource.invoke chatgpt.tokens.use.direct",
            "expires_in": 1800,
        }
        params = {"state": ["expected-state"], "client_id": ["oaiapp-test"], "code": ["code-test"]}
        with (
            mock.patch.object(CA, "_request_token", return_value=token_result) as exchange,
            mock.patch.object(CA, "_verify_id_token", return_value={"sub": "account-test", "email": "a@example.test"}),
            mock.patch.object(CA, "_write") as store,
        ):
            CA._finish(self.vault, params, pending)
        self.assertEqual(exchange.call_args.args[0]["client_id"], "oaiapp-test")
        self.assertEqual(exchange.call_args.args[0]["code_verifier"], "pkce-verifier")
        self.assertEqual(store.call_args.args[1]["subject"], "account-test")
        self.assertEqual(store.call_args.args[1]["refresh_token"], "refresh-test")
        self.assertEqual(store.call_args.args[1]["client_id"], "oaiapp-test")

        with self.assertRaises(CA.AuthError):
            CA._finish(self.vault, {**params, "state": ["wrong"]}, pending)

    def test_chatgpt_id_token_signature_audience_nonce_and_expiry_are_verified(self):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        def b64(value):
            return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        numbers = private.public_key().public_numbers()
        jwk = {
            "kid": "key-test",
            "kty": "RSA",
            "n": b64(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big").lstrip(b"\x00")),
            "e": b64(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big").lstrip(b"\x00")),
        }
        header = b64(json.dumps({"alg": "RS256", "kid": "key-test"}).encode())
        body = b64(
            json.dumps(
                {
                    "iss": CA.ISSUER,
                    "aud": "oaiapp-test",
                    "exp": int(time.time()) + 300,
                    "nonce": "nonce-test",
                    "sub": "account-test",
                }
            ).encode()
        )
        signing_input = f"{header}.{body}".encode("ascii")
        signature = private.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        token = f"{header}.{body}.{b64(signature)}"
        response = io.BytesIO(json.dumps({"keys": [jwk]}).encode())
        with mock.patch.object(CA.net, "urlopen", return_value=response):
            claims = CA._verify_id_token(token, "oaiapp-test", "nonce-test")
        self.assertEqual(claims["sub"], "account-test")
        with mock.patch.object(CA.net, "urlopen", return_value=io.BytesIO(json.dumps({"keys": [jwk]}).encode())):
            with self.assertRaises(CA.AuthError):
                CA._verify_id_token(token, "oaiapp-test", "wrong-nonce")

    def test_codex_stream_uses_read_only_turn_and_deletes_temporary_thread(self):
        class FakeServer:
            events = []
            calls = []

            def __init__(self, *_args, **_kwargs):
                self.lines = queue.Queue()

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def request(self, method, params=None, on_message=None, timeout=None):
                self.calls.append((method, params or {}))
                if method == "account/read":
                    return {"account": {"type": "chatgpt"}}
                if method == "thread/start":
                    return {"thread": {"id": "thread-test"}}
                if method == "turn/start":
                    for event in self.events:
                        on_message(event)
                    return {"turn": {"id": "turn-test"}}
                return {}

            def send(self, payload):
                self.calls.append(("send", payload))

        FakeServer.events = [
            {"method": "item/agentMessage/delta", "params": {"delta": "Ответ"}},
            {"method": "turn/completed", "params": {"turn": {"status": "completed"}}},
        ]
        FakeServer.calls = []
        with (
            mock.patch.object(CS, "AppServer", FakeServer),
            mock.patch("mnema.chat.codex_auth.access_token", return_value="test-oauth-token"),
        ):
            answer = "".join(CS.stream(self.vault, "gpt-5", "", [{"role": "user", "text": "Привет"}]))
        self.assertEqual(answer, "Ответ")
        calls = dict((method, params) for method, params in FakeServer.calls if method != "send")
        self.assertEqual(calls["thread/start"]["sandbox"], "read-only")
        self.assertEqual(calls["turn/start"]["approvalPolicy"], "never")
        self.assertEqual(calls["turn/start"]["sandboxPolicy"]["type"], "readOnly")
        self.assertEqual(calls["thread/delete"]["threadId"], "thread-test")


if __name__ == "__main__":
    unittest.main()
