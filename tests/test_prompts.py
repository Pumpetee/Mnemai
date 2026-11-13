"""Prompts for recurring tasks: offered on the second similar request, written only with consent, then reused."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.agent import profile as P  # noqa: E402
from mnema.chat import engine as CH, prompts as PRM, providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402
from test_core import fill  # noqa: E402

NL = chr(10)


class Fake:
    def __init__(self):
        self.calls = []

    def __call__(self, vault, pid, model, system, messages, stop=None, usage=None, meta=None):
        if system.startswith("Ты придумываешь"):
            yield "Письмо клиенту"
            return
        self.calls.append({"system": system, "messages": messages})
        if "Ты пишешь промт" in messages[-1]["text"]:
            yield (
                "НАЗВАНИЕ: Письмо клиенту о задержке"
                + NL
                + "КОГДА: письма клиентам о сдвиге сроков"
                + NL
                + "ПРОМТ:"
                + NL
                + "1. Извиниться коротко."
                + NL
                + "2. Новый срок."
            )
            return
        yield "Готово, вот письмо."


class TestPrompts(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir / "v")
        init_vault(self.v)
        fill(self.v)
        self.orig, PR.stream = PR.stream, Fake()

    def tearDown(self):
        PR.stream = self.orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def send(self, text):
        return CH.send(self.v, text, model="claude_code:", sync=True, learn=False, terms=False)

    def test_second_similar_task_offers_writes_and_reuses(self):
        r1 = self.send("Напиши письмо клиенту о задержке поставки на неделю")
        self.assertFalse(r1.get("offer"))  # first time: just done
        r2 = self.send("Напиши письмо клиенту о задержке поставки на две недели")
        self.assertTrue(r2.get("offer"))
        c = CH.load_chat(self.v, r2["chat"])
        self.assertEqual(c["messages"][-1]["kind"], "prompt_offer")
        self.assertIn("Записать рецепт", c["messages"][-1]["text"])
        CH.answer_offer(self.v, r2["chat"], "write", sync=True)
        files = PRM.all_prompts(self.v)
        self.assertEqual([p["name"] for p in files], ["Письмо клиенту о задержке"])
        self.assertIn("Новый срок", files[0]["body"])
        c = CH.load_chat(self.v, r2["chat"])
        self.assertEqual(c["messages"][-1]["kind"], "prompt_offer")  # the card stays after the answer
        self.assertEqual(c["messages"][-1]["offer"]["choice"], "write")
        self.assertEqual(c["messages"][-1]["offer"]["name"], "Письмо клиенту о задержке")
        # the answer came first: saving the recipe must not answer the same task a second time
        answers = [m for m in c["messages"] if m.get("role") == "assistant" and m.get("kind") != "prompt_offer"]
        self.assertEqual(len(answers), 1)
        r3 = self.send("Напиши письмо клиенту о задержке поставки на три дня")
        self.assertFalse(r3.get("offer"))
        m = CH.load_chat(self.v, r3["chat"])["messages"][-1]
        self.assertEqual(m["prompt"], "Письмо клиенту о задержке")
        self.assertIn("Промт владельца на эту задачу", PR.stream.calls[-1]["system"])
        # the offer card itself never goes to the model as part of the conversation
        self.assertFalse(any("Записать рецепт" in m["text"] for m in PR.stream.calls[-1]["messages"]))
        self.assertEqual(PRM.all_prompts(self.v)[0]["uses"], 1)  # used once, by the next similar task

    def test_never_and_off(self):
        self.send("Составь отчёт по продажам за неделю для команды")
        r = self.send("Составь отчёт по продажам за месяц для команды")
        CH.answer_offer(self.v, r["chat"], "never", sync=True)
        self.assertFalse(self.send("Составь отчёт по продажам за квартал для команды").get("offer"))
        self.assertEqual(PRM.all_prompts(self.v), [])
        P.save(self.v, {"prompts_mode": "off"})
        self.send("Переведи договор поставки на английский язык")
        self.assertFalse(self.send("Переведи договор поставки на немецкий язык").get("offer"))

    def test_questions_are_not_tasks(self):
        self.send("Что такое юнит экономика подписки и как её считать")
        self.assertFalse(self.send("Что такое юнит экономика подписки простыми словами").get("offer"))

    def test_every_task_mode(self):
        P.save(self.v, {"prompts_mode": "every"})
        self.assertTrue(self.send("Подготовь план созвона с командой на завтра").get("offer"))


if __name__ == "__main__":
    unittest.main()


class TestRecipesFolder(unittest.TestCase):
    def test_old_prompts_folder_is_renamed_once(self):
        import tempfile
        from mnema.chat import prompts as PRM
        from mnema.vault import Vault

        v = Vault(Path(tempfile.mkdtemp()))
        old = v.root / "90 System" / "Prompts"
        old.mkdir(parents=True)
        (old / "Отчёт.md").write_text("---\nname: Отчёт\n---\nшаги", encoding="utf-8")
        d = PRM.folder(v)
        self.assertEqual(d, v.root / "90 System" / "Recipes")
        self.assertTrue((d / "Отчёт.md").exists())
        self.assertFalse(old.exists())
