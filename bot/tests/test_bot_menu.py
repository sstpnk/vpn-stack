import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import telegram_stubs


def load_bot():
    telegram_stubs.install()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.modules.pop("bot", None)
    return importlib.import_module("bot")


class BotMenuTest(unittest.TestCase):
    def test_main_keyboard_uses_two_buttons_per_row(self):
        bot = load_bot()

        row_lengths = [len(row) for row in bot.MAIN_KEYBOARD.keyboard]
        self.assertEqual(row_lengths, [2, 2, 2, 2])

    def test_inline_menu_uses_two_buttons_per_row(self):
        bot = load_bot()

        row_lengths = [len(row) for row in bot.INLINE_MENU.inline_keyboard]
        self.assertEqual(row_lengths, [2, 2, 2, 2])


if __name__ == "__main__":
    unittest.main()
