"""Minimal telegram stubs so bot.py can be imported without the real library."""

import sys
import types


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


class NetworkError(Exception):
    pass


class TelegramError(Exception):
    pass


def install():
    telegram_stub = types.ModuleType("telegram")
    telegram_stub.InlineKeyboardButton = InlineKeyboardButton
    telegram_stub.InlineKeyboardMarkup = InlineKeyboardMarkup
    telegram_stub.ReplyKeyboardMarkup = ReplyKeyboardMarkup
    telegram_stub.Update = object

    telegram_error_stub = types.ModuleType("telegram.error")
    telegram_error_stub.NetworkError = NetworkError
    telegram_error_stub.TelegramError = TelegramError

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
