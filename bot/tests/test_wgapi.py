import importlib
import os
import sys
import types
import unittest
from pathlib import Path


class FakeSession:
    def __init__(self):
        self.verify = True
        self.cookies = []


def install_requests_stub():
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = FakeSession
    sys.modules["requests"] = requests_stub


class WGEasyAPITest(unittest.TestCase):
    def setUp(self):
        install_requests_stub()
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        sys.modules.pop("wgapi", None)
        os.environ["WG_EASY_URL"] = "https://wg-easy:51821"
        os.environ["WG_EASY_PASSWORD"] = "secret"

    def test_disables_tls_verification_when_configured(self):
        os.environ["WG_EASY_VERIFY_TLS"] = "false"
        wgapi = importlib.import_module("wgapi")

        api = wgapi.WGEasyAPI()

        self.assertFalse(api.session.verify)

    def test_keeps_tls_verification_enabled_by_default(self):
        os.environ.pop("WG_EASY_VERIFY_TLS", None)
        wgapi = importlib.import_module("wgapi")

        api = wgapi.WGEasyAPI()

        self.assertTrue(api.session.verify)


if __name__ == "__main__":
    unittest.main()
