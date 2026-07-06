# Public Host Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic domain-or-IP public host setting while preserving existing `WG_HOST` deployments.

**Architecture:** `PUBLIC_HOST` becomes the documented shared setting. New installs write `PUBLIC_HOST`, `WG_HOST`, and `XRAY_PUBLIC_HOST` to `.env`; runtime code keeps using existing service-specific variables with a new Xray fallback to `PUBLIC_HOST`.

**Tech Stack:** Bash setup script, Docker Compose environment variables, Python Xray manager tests, Markdown docs.

---

### Task 1: Xray Public Host Fallback

**Files:**
- Modify: `bot/src/xray_manager.py`
- Modify: `bot/tests/test_xray_manager.py`

- [x] **Step 1: Write the failing test**

Add a test method to `XrayManagerTest`:

```python
def test_public_host_falls_back_to_shared_public_host(self):
    os.environ["XRAY_PUBLIC_HOST"] = ""
    os.environ["PUBLIC_HOST"] = "vpn.example.com"
    manager = XrayManager(FakeDocker(self.container))

    clients = manager.list_clients()
    outbound = clients[0]["client_config"]["outbounds"][0]

    self.assertIn("@vpn.example.com:8443", clients[0]["link"])
    self.assertEqual(
        outbound["settings"]["vnext"][0]["address"],
        "vpn.example.com",
    )
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest bot.tests.test_xray_manager.XrayManagerTest.test_public_host_falls_back_to_shared_public_host`

Expected: FAIL because `XrayManager` falls back from empty `XRAY_PUBLIC_HOST` directly to `WG_HOST`.

- [x] **Step 3: Implement minimal fallback**

Change `XrayManager.__init__` so `self.public_host` reads:

```python
self.public_host = (
    os.environ.get("XRAY_PUBLIC_HOST")
    or os.environ.get("PUBLIC_HOST")
    or os.environ.get("WG_HOST", "")
)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest bot.tests.test_xray_manager.XrayManagerTest.test_public_host_falls_back_to_shared_public_host`

Expected: PASS.

### Task 2: Setup Script Host Prompt

**Files:**
- Modify: `setup.sh`

- [x] **Step 1: Update new `.env` generation**

Change the interactive prompt from:

```bash
read -p "Server IP address: " WG_HOST
```

to:

```bash
read -p "Public server host (domain or IP): " PUBLIC_HOST
WG_HOST=$PUBLIC_HOST
XRAY_PUBLIC_HOST=$PUBLIC_HOST
```

Write all three variables under the server configuration block:

```dotenv
PUBLIC_HOST=$PUBLIC_HOST
WG_HOST=$WG_HOST
WG_EASY_PASSWORD=$WG_EASY_PASSWORD
WG_PORT=$WG_PORT
XRAY_PORT=$XRAY_PORT
XRAY_PUBLIC_HOST=$XRAY_PUBLIC_HOST
```

- [x] **Step 2: Update setup completion output**

Change the Web UI line to use the public host variable:

```bash
echo "Web UI: http://$PUBLIC_HOST:51821"
```

### Task 3: Documentation

**Files:**
- Modify: `README.md`

- [x] **Step 1: Update env examples**

In each `.env` example, add `PUBLIC_HOST=example.com` before `WG_HOST`, and show `WG_HOST=${PUBLIC_HOST}` conceptually by using the same example host value. Leave `XRAY_PUBLIC_HOST=` documented as optional but explain its default chain.

- [x] **Step 2: Update variable tables**

Document:

```markdown
| `PUBLIC_HOST` | none | preferred public DNS name or IPv4 address used by generated client configs |
```

Update `WG_HOST` to describe it as the AmneziaWG endpoint host, defaulting operationally to the same value generated from setup for new installs. Update `XRAY_PUBLIC_HOST` default text to `PUBLIC_HOST`, then `WG_HOST`.

- [x] **Step 3: Update troubleshooting text**

Change endpoint checks from "public IP" to "public DNS name or IP" and add a short note that DNS users should update the A record after a VPS IP change, then recreate or re-download client configs only if the generated endpoint itself changed.

### Task 4: Verification

**Files:**
- Read: `bot/tests/test_xray_manager.py`
- Read: `setup.sh`
- Read: `README.md`

- [x] **Step 1: Run Xray tests**

Run: `python -m unittest bot.tests.test_xray_manager`

Expected: all tests pass.

- [x] **Step 2: Inspect git diff**

Run: `git diff -- bot/src/xray_manager.py bot/tests/test_xray_manager.py setup.sh README.md docs/superpowers/specs/2026-07-06-public-host-design.md docs/superpowers/plans/2026-07-06-public-host.md`

Expected: diff contains only public host support, docs, tests, and no private domain.
