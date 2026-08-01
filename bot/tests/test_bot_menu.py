import importlib
import sys
import types
import unittest
from pathlib import Path


class InlineKeyboardButton:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data


class InlineKeyboardMarkup:
    def __init__(self, inline_keyboard):
        self.inline_keyboard = inline_keyboard


class ReplyKeyboardMarkup:
    def __init__(self, keyboard, resize_keyboard=False):
        self.keyboard = keyboard
        self.resize_keyboard = resize_keyboard


def install_stubs():
    telegram_stub = types.ModuleType("telegram")
    telegram_stub.InlineKeyboardButton = InlineKeyboardButton
    telegram_stub.InlineKeyboardMarkup = InlineKeyboardMarkup
    telegram_stub.ReplyKeyboardMarkup = ReplyKeyboardMarkup
    telegram_stub.Update = object

    telegram_error_stub = types.ModuleType("telegram.error")
    telegram_error_stub.NetworkError = RuntimeError

    telegram_ext_stub = types.ModuleType("telegram.ext")
    for name in [
        "Application",
        "CallbackQueryHandler",
        "CommandHandler",
        "ContextTypes",
        "ConversationHandler",
        "MessageHandler",
    ]:
        setattr(telegram_ext_stub, name, object)
    telegram_ext_stub.filters = types.SimpleNamespace(TEXT=object(), COMMAND=object())

    wgapi_stub = types.ModuleType("wgapi")
    wgapi_stub.WGEasyAPI = lambda: object()

    xray_manager_stub = types.ModuleType("xray_manager")
    xray_manager_stub.XrayManager = lambda: object()

    sys.modules["telegram"] = telegram_stub
    sys.modules["telegram.error"] = telegram_error_stub
    sys.modules["telegram.ext"] = telegram_ext_stub
    sys.modules["wgapi"] = wgapi_stub
    sys.modules["xray_manager"] = xray_manager_stub


class BotMenuTest(unittest.TestCase):
    def test_inline_menu_uses_two_buttons_per_row(self):
        install_stubs()
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        sys.modules.pop("bot", None)

        bot = importlib.import_module("bot")

        row_lengths = [len(row) for row in bot.INLINE_MENU.inline_keyboard]
        self.assertEqual(row_lengths, [2, 2, 2, 2])


if __name__ == "__main__":
    unittest.main()
