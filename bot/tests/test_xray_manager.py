import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

docker_stub = types.ModuleType("docker")
docker_stub.from_env = lambda: None
sys.modules.setdefault("docker", docker_stub)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xray_manager import XrayManager


class ExecResult:
    def __init__(self, exit_code=0, output=b""):
        self.exit_code = exit_code
        self.output = output


class FakeContainer:
    def __init__(self):
        self.status = "running"
        self.restart_count = 0
        self.reject_config = False

    def exec_run(self, command):
        if command[:2] == ["xray", "x25519"]:
            return ExecResult(output=b"PrivateKey: hidden\nPassword: PUBLIC_KEY\n")
        if command[:3] == ["xray", "run", "-test"]:
            if self.reject_config:
                return ExecResult(1, b"invalid config")
            return ExecResult(0, b"Configuration OK.")
        raise AssertionError(f"Unexpected command: {command}")

    def restart(self, timeout):
        self.restart_count += 1

    def reload(self):
        pass


class FakeContainers:
    def __init__(self, container):
        self.container = container

    def get(self, name):
        if name != "vpn-xray":
            raise AssertionError(name)
        return self.container


class FakeDocker:
    def __init__(self, container):
        self.containers = FakeContainers(container)


def sample_config():
    return {
        "inbounds": [{
            "protocol": "vless",
            "settings": {
                "clients": [{
                    "id": "11111111-1111-4111-8111-111111111111",
                    "flow": "xtls-rprx-vision",
                    "email": "existing",
                }],
                "decryption": "none",
            },
            "streamSettings": {
                "security": "reality",
                "realitySettings": {
                    "target": "www.google.com:443",
                    "serverNames": ["www.google.com"],
                    "privateKey": "PRIVATE_KEY",
                    "shortIds": ["11111111"],
                },
            },
        }],
        "outbounds": [{"protocol": "freedom"}],
    }


class XrayManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.config_path.write_text(
            json.dumps(sample_config()),
            encoding="utf-8",
        )
        self.container = FakeContainer()
        os.environ.update({
            "XRAY_CONFIG_PATH": str(self.config_path),
            "XRAY_CONTAINER": "vpn-xray",
            "XRAY_PUBLIC_HOST": "203.0.113.10",
            "XRAY_PORT": "8443",
            "XRAY_SERVER_NAME": "www.google.com",
            "XRAY_FINGERPRINT": "randomized",
            "XRAY_RESTART_STABILITY_SECONDS": "0",
        })
        self.manager = XrayManager(FakeDocker(self.container))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_lists_links_and_client_json(self):
        clients = self.manager.list_clients()

        self.assertEqual(len(clients), 1)
        self.assertIn("sni=www.google.com", clients[0]["link"])
        self.assertIn("sid=11111111", clients[0]["link"])
        outbound = clients[0]["client_config"]["outbounds"][0]
        self.assertEqual(outbound["mux"]["xudpProxyUDP443"], "reject")
        self.assertEqual(
            outbound["streamSettings"]["realitySettings"]["password"],
            "PUBLIC_KEY",
        )
        self.assertIn("spx=%2F", clients[0]["link"])
        self.assertNotIn("spx=%2F11111111", clients[0]["link"])
        self.assertEqual(
            outbound["streamSettings"]["realitySettings"]["spiderX"],
            "/",
        )

    def test_legacy_client_link_does_not_invent_flow(self):
        config = sample_config()
        del config["inbounds"][0]["settings"]["clients"][0]["flow"]
        self.config_path.write_text(json.dumps(config), encoding="utf-8")

        client = self.manager.list_clients()[0]

        self.assertNotIn("flow=", client["link"])
        user = client["client_config"]["outbounds"][0]["settings"]["vnext"][0]["users"][0]
        self.assertNotIn("flow", user)

    def test_creates_and_deletes_client(self):
        created = self.manager.create_client("laptop")
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        clients = config["inbounds"][0]["settings"]["clients"]
        short_ids = config["inbounds"][0]["streamSettings"]["realitySettings"]["shortIds"]

        self.assertEqual(clients[-1]["email"], "laptop")
        self.assertEqual(clients[-1]["flow"], "xtls-rprx-vision")
        self.assertIn(created["short_id"], short_ids)
        self.assertEqual(self.container.restart_count, 1)

        deleted = self.manager.delete_client(created["id"])
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(deleted["name"], "laptop")
        self.assertNotIn(
            created["id"],
            [client["id"] for client in config["inbounds"][0]["settings"]["clients"]],
        )
        self.assertEqual(self.container.restart_count, 2)

    def test_restores_config_when_xray_rejects_candidate(self):
        original = self.config_path.read_bytes()
        self.container.reject_config = True

        with self.assertRaisesRegex(ValueError, "Xray rejected"):
            self.manager.create_client("broken")

        self.assertEqual(self.config_path.read_bytes(), original)
        self.assertEqual(self.container.restart_count, 0)


if __name__ == "__main__":
    unittest.main()
