"""Mnemai answers about itself from its knowledge base, not from the engine it runs on: "Что ты умеешь делать с pdf?"
must describe Mnemai's file handling, not the engine's tools, and must not search the web."""

import tempfile
import unittest
from pathlib import Path

from mnema import web
from mnema.chat import selfknow as SK
from mnema.chat.engine import system_prompt
from mnema.memory import init_vault
from mnema.vault import Vault


class Knowledge(unittest.TestCase):
    def setUp(self):
        self.v = Vault(Path(tempfile.mkdtemp()))
        init_vault(self.v)

    def test_base_is_there_and_split(self):
        titles = [t for t, _ in SK.kb_sections()]
        self.assertGreater(len(titles), 25)
        for t in ("Файлы и документы, в том числе PDF", "Интернет", "Чего Mnemai не умеет", "Кто из ИИ что видит"):
            self.assertIn(t, titles)

    def test_pdf_question_gets_files_section_and_no_web(self):
        q = "Что ты умеешь делать с pdf?"
        self.assertTrue(SK.about_mnema(q))
        self.assertFalse(web.should_search(q))
        kb = SK.kb_for(q)
        self.assertIn("## Файлы и документы, в том числе PDF", kb)
        self.assertIn("## Действия на компьютере", kb)  # making a PDF is an action now, with the owner's word
        self.assertIn("Терминал и управление компьютером", kb)  # the model knows about its PC access
        self.assertIn("не заполняет формы PDF", kb)
        sp = system_prompt(self.v, "claude_code", query=q)
        self.assertIn("Ты — Mnemai", sp)
        self.assertIn("База знаний Mnemai", sp)

    def test_ordinary_task_gets_no_base(self):
        q = "Напиши письмо клиенту о задержке поставки"
        self.assertFalse(SK.about_mnema(q))
        self.assertNotIn("База знаний Mnemai", system_prompt(self.v, "claude_code", query=q))


if __name__ == "__main__":
    unittest.main()
