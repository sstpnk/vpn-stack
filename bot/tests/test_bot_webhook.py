import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import telegram_stubs


def load_bot():
    telegram_stubs.install()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.modules.pop("bot", None)
    return importlib.import_module("bot")


class FakeBot:
    def __init__(self, url=""):
        self.url = url
        self.deleted = []

    async def get_webhook_info(self):
        return types.SimpleNamespace(url=self.url)

    async def delete_webhook(self, drop_pending_updates=False):
        self.deleted.append(drop_pending_updates)
        self.url = ""


class FakeApp:
    def __init__(self, bot):
        self.bot = bot
        self.bot_data = {}


class WebhookGuardTest(unittest.TestCase):
    def setUp(self):
        self.bot = load_bot()

    def test_removes_webhook_left_on_the_bot(self):
        fake_bot = FakeBot("https://tele.example.com/tg/webhook/123")
        app = FakeApp(fake_bot)

        asyncio.run(self.bot.delete_webhook_if_set(app, drop_pending=True))

        self.assertEqual(fake_bot.deleted, [True])
        self.assertEqual(fake_bot.url, "")

    def test_keeps_quiet_when_no_webhook_is_set(self):
        fake_bot = FakeBot("")
        app = FakeApp(fake_bot)

        asyncio.run(self.bot.delete_webhook_if_set(app, drop_pending=False))

        self.assertEqual(fake_bot.deleted, [])

    def test_startup_arms_watchdog_and_shutdown_disarms_it(self):
        async def scenario():
            fake_bot = FakeBot("")
            app = FakeApp(fake_bot)

            await self.bot.on_startup(app)
            watchdog = app.bot_data["webhook_watchdog"]
            self.assertFalse(watchdog.done())

            await self.bot.on_shutdown(app)
            self.assertNotIn("webhook_watchdog", app.bot_data)
            self.assertTrue(watchdog.cancelled())

        asyncio.run(scenario())

    def test_watchdog_removes_a_webhook_registered_later(self):
        async def scenario():
            fake_bot = FakeBot("")
            app = FakeApp(fake_bot)
            self.bot.WEBHOOK_CHECK_INTERVAL = 0.01

            watchdog = asyncio.create_task(self.bot.watch_for_webhook(app))
            fake_bot.url = "https://tele.example.com/tg/webhook/123"
            await asyncio.sleep(0.05)
            watchdog.cancel()

            self.assertTrue(fake_bot.deleted)
            self.assertEqual(fake_bot.url, "")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
