"""A model without tools may leak a DSML tool block into the visible answer; it must be hidden."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat.engine import strip_tool_markup  # noqa: E402


class Dsml(unittest.TestCase):
    def test_fullwidth_dsml_block_is_hidden(self):
        raw = "<｜｜DSML｜｜ calls>\n<｜｜DSML｜｜ inDSML｜｜ parameter>\n</｜｜DSML｜｜ invoke>\n</｜｜DSML｜｜ calls>"
        self.assertEqual(strip_tool_markup(raw), "")
        self.assertEqual(strip_tool_markup("Ответ.\n" + raw), "Ответ.")

    def test_normal_answer_survives(self):
        self.assertEqual(strip_tool_markup("Привет"), "Привет")
        self.assertEqual(strip_tool_markup(""), "")


if __name__ == "__main__":
    unittest.main()
