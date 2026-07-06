import json
import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import quote, urlencode

import docker


class XrayManager:
    def __init__(self, docker_client=None):
        self.config_path = Path(os.environ.get("XRAY_CONFIG_PATH", "/xray-config/config.json"))
        self.container_name = os.environ.get("XRAY_CONTAINER", "vpn-xray")
        self.public_host = (
            os.environ.get("XRAY_PUBLIC_HOST")
            or os.environ.get("PUBLIC_HOST")
            or os.environ.get("WG_HOST", "")
        )
        self.public_port = int(os.environ.get("XRAY_PORT", "8443"))
        self.server_name = os.environ.get("XRAY_SERVER_NAME", "www.google.com")
        self.fingerprint = os.environ.get("XRAY_FINGERPRINT", "randomized")
        self.restart_stability_seconds = float(
            os.environ.get("XRAY_RESTART_STABILITY_SECONDS", "2")
        )
        self.docker = docker_client or docker.from_env()
        self._lock = threading.Lock()

    def list_clients(self) -> list[dict]:
        config = self._load_config()
        inbound, reality = self._get_reality_inbound(config)
        public_key = self._get_public_key(reality["privateKey"])
        short_ids = reality.get("shortIds", [])

        result = []
        server_name = self._server_name_for_config(reality)
        for index, client in enumerate(inbound["settings"].get("clients", [])):
            client_id = client["id"]
            flow = client.get("flow")
            short_id = self._assigned_short_id(client_id, index, short_ids)
            name = client.get("email") or f"vless-{client_id[:8]}"
            result.append({
                "id": client_id,
                "name": name,
                "short_id": short_id,
                "link": self._build_link(
                    client_id,
                    name,
                    short_id,
                    public_key,
                    server_name,
                    flow,
                ),
                "client_config": self._build_client_config(
                    client_id,
                    short_id,
                    public_key,
                    server_name,
                    flow,
                ),
                "index": index,
            })
        return result

    def create_client(self, name: str) -> dict:
        with self._lock:
            name = self._validate_name(name)
            config = self._load_config()
            inbound, reality = self._get_reality_inbound(config)
            clients = inbound["settings"].setdefault("clients", [])
            short_ids = reality.setdefault("shortIds", [])

            existing_ids = {client["id"] for client in clients}
            existing_short_ids = set(short_ids)
            while True:
                client_id = str(uuid.uuid4())
                short_id = self._short_id_for_client(client_id)
                if client_id not in existing_ids and short_id not in existing_short_ids:
                    break

            clients.append({
                "id": client_id,
                "flow": "xtls-rprx-vision",
                "email": name,
            })
            short_ids.append(short_id)
            self._apply_config(config)

            public_key = self._get_public_key(reality["privateKey"])
            server_name = self._server_name_for_config(reality)
            return {
                "id": client_id,
                "name": name,
                "short_id": short_id,
                "link": self._build_link(
                    client_id,
                    name,
                    short_id,
                    public_key,
                    server_name,
                    "xtls-rprx-vision",
                ),
                "client_config": self._build_client_config(
                    client_id,
                    short_id,
                    public_key,
                    server_name,
                    "xtls-rprx-vision",
                ),
            }

    def delete_client(self, client_id: str) -> dict:
        with self._lock:
            config = self._load_config()
            inbound, reality = self._get_reality_inbound(config)
            clients = inbound["settings"].setdefault("clients", [])
            client_index = next(
                (index for index, item in enumerate(clients) if item.get("id") == client_id),
                None,
            )
            if client_index is None:
                raise ValueError("VLESS connection not found")

            client = clients.pop(client_index)
            short_ids = reality.setdefault("shortIds", [])
            short_id = self._assigned_short_id(client_id, client_index, short_ids)
            if short_id in short_ids:
                short_ids.remove(short_id)

            self._apply_config(config)
            return {
                "id": client_id,
                "name": client.get("email") or f"vless-{client_id[:8]}",
            }

    def _load_config(self) -> dict:
        with self.config_path.open("r", encoding="utf-8") as config_file:
            return json.load(config_file)

    @staticmethod
    def _get_reality_inbound(config: dict) -> tuple[dict, dict]:
        for inbound in config.get("inbounds", []):
            stream = inbound.get("streamSettings", {})
            if inbound.get("protocol") == "vless" and stream.get("security") == "reality":
                settings = inbound.setdefault("settings", {})
                settings.setdefault("clients", [])
                reality = stream.setdefault("realitySettings", {})
                if not reality.get("privateKey"):
                    raise ValueError("Reality privateKey is missing")
                return inbound, reality
        raise ValueError("VLESS Reality inbound was not found")

    def _get_public_key(self, private_key: str) -> str:
        container = self.docker.containers.get(self.container_name)
        result = container.exec_run(["xray", "x25519", "-i", private_key])
        output = result.output.decode("utf-8", errors="replace")
        if result.exit_code != 0:
            raise RuntimeError(f"Failed to derive Reality public key: {output.strip()}")

        match = re.search(r"^(?:Password|PublicKey)(?:\s+\(PublicKey\))?:\s*(\S+)", output, re.MULTILINE)
        if not match:
            raise RuntimeError("Xray did not return a Reality public key")
        return match.group(1)

    def _apply_config(self, config: dict):
        original = self.config_path.read_bytes()
        pending_path = None
        config_replaced = False
        container = self.docker.containers.get(self.container_name)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.config_path.parent,
                prefix="config.",
                suffix=".pending.json",
                delete=False,
            ) as pending:
                json.dump(config, pending, ensure_ascii=False, indent=2)
                pending.write("\n")
                pending.flush()
                os.fsync(pending.fileno())
                pending_path = Path(pending.name)

            container_pending_path = f"/etc/xray/{pending_path.name}"
            result = container.exec_run([
                "xray",
                "run",
                "-test",
                "-c",
                container_pending_path,
            ])
            if result.exit_code != 0:
                raise ValueError("Xray rejected the generated config")

            os.replace(pending_path, self.config_path)
            pending_path = None
            config_replaced = True
            container.restart(timeout=20)
            time.sleep(self.restart_stability_seconds)
            container.reload()
            if container.status != "running":
                raise RuntimeError(f"Xray container status is {container.status}")
        except Exception:
            if config_replaced:
                self.config_path.write_bytes(original)
                try:
                    container.restart(timeout=20)
                except Exception:
                    pass
            raise
        finally:
            if pending_path is not None:
                pending_path.unlink(missing_ok=True)

    def _build_link(
        self,
        client_id: str,
        name: str,
        short_id: str,
        public_key: str,
        server_name: str,
        flow: str | None,
    ) -> str:
        if not self.public_host:
            raise ValueError("XRAY_PUBLIC_HOST, PUBLIC_HOST, or WG_HOST is not configured")

        query_parameters = {
            "encryption": "none",
            "type": "tcp",
            "security": "reality",
            "fp": self.fingerprint,
            "sni": server_name,
            "pbk": public_key,
            "sid": short_id,
            "spx": "/",
        }
        if flow:
            query_parameters["flow"] = flow
        query = urlencode(query_parameters)
        return (
            f"vless://{client_id}@{self.public_host}:{self.public_port}"
            f"?{query}#{quote(name, safe='')}"
        )

    def _build_client_config(
        self,
        client_id: str,
        short_id: str,
        public_key: str,
        server_name: str,
        flow: str | None,
    ) -> dict:
        user = {
            "id": client_id,
            "encryption": "none",
        }
        if flow:
            user["flow"] = flow

        return {
            "outbounds": [{
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": self.public_host,
                        "port": self.public_port,
                        "users": [user],
                    }],
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "fingerprint": self.fingerprint,
                        "serverName": server_name,
                        "password": public_key,
                        "shortId": short_id,
                        "spiderX": "/",
                    },
                },
                "mux": {
                    "enabled": True,
                    "concurrency": 8,
                    "xudpConcurrency": 8,
                    "xudpProxyUDP443": "reject",
                },
            }],
        }

    @staticmethod
    def _short_id_for_client(client_id: str) -> str:
        return client_id.replace("-", "")[:8].lower()

    @classmethod
    def _assigned_short_id(cls, client_id: str, index: int, short_ids: list[str]) -> str:
        derived = cls._short_id_for_client(client_id)
        if derived in short_ids:
            return derived
        if index < len(short_ids):
            return short_ids[index]
        return derived

    def _server_name_for_config(self, reality: dict) -> str:
        server_names = reality.get("serverNames") or []
        if self.server_name in server_names:
            return self.server_name
        if server_names:
            return server_names[0]
        raise ValueError("Reality serverNames is empty")

    @staticmethod
    def _validate_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("Name cannot be empty")
        if len(name) > 64:
            raise ValueError("Name must be 64 characters or fewer")
        if any(ord(character) < 32 for character in name):
            raise ValueError("Name contains unsupported control characters")
        return name
