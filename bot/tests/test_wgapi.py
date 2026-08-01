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


class FakeUrllib3:
    class exceptions:
        class InsecureRequestWarning(Warning):
            pass

    def __init__(self):
        self.disabled_warning = None

    def disable_warnings(self, warning):
        self.disabled_warning = warning


def install_requests_stub():
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = FakeSession
    requests_stub.packages = types.SimpleNamespace(urllib3=FakeUrllib3())
    sys.modules["requests"] = requests_stub
    return requests_stub


class WGEasyAPITest(unittest.TestCase):
    def setUp(self):
        self.requests_stub = install_requests_stub()
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        sys.modules.pop("wgapi", None)
        os.environ["WG_EASY_URL"] = "https://wg-easy:51821"
        os.environ["WG_EASY_PASSWORD"] = "secret"

    def test_disables_tls_verification_when_configured(self):
        os.environ["WG_EASY_VERIFY_TLS"] = "false"
        wgapi = importlib.import_module("wgapi")

        api = wgapi.WGEasyAPI()

        self.assertFalse(api.session.verify)
        urllib3 = self.requests_stub.packages.urllib3
        self.assertIs(
            urllib3.disabled_warning,
            urllib3.exceptions.InsecureRequestWarning,
        )

    def test_keeps_tls_verification_enabled_by_default(self):
        os.environ.pop("WG_EASY_VERIFY_TLS", None)
        wgapi = importlib.import_module("wgapi")

        api = wgapi.WGEasyAPI()

        self.assertTrue(api.session.verify)
        self.assertIsNone(self.requests_stub.packages.urllib3.disabled_warning)


if __name__ == "__main__":
    unittest.main()
