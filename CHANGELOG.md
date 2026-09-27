# Changelog

All notable changes to VPN Stack are documented in this file.

The project uses semantic versioning for published releases.

## [1.1.0] - 2026-09-27

### Added

- AmneziaWG 3.1 server-generated client configuration contract.
- AWG 3.1 fields in generated peer configs: `S3`, `S4`,
  `HeaderProtectionKey`, `ContentPaddingAddition`, `RekeyAfterTime`,
  `RekeyTimeout`, `RejectAfterTime`, `KeepaliveTimeout`,
  `MaxHandshakeAttempts`, `RandomTrailers`, and `DisableCookies`.
- Tests for AWG API defaults, AWG 3.1 config generation, and smoke parsing.

### Changed

- AmneziaWG Easy now builds on `amneziavpn/amneziawg-go:3.1.20260828`.
- Runtime AmneziaWG state is mounted at `/etc/amnezia/amneziawg`.
- Android guidance now recommends FreedomCat for this stack.
- The default protocol mode stays compatible with existing legacy installs;
  AWG 3.1 is enabled with `AMNEZIA_PROTOCOL_VERSION=3.1`.

### Operations

- Existing `.env`, `data/wg-easy`, and `xray-config/config.json` state should
  be preserved during upgrade.
- Before enabling AWG 3.1 on a live server, confirm that target clients can
  import the generated profiles.

## [1.0.1] - 2026-07-21

### Added

- Self-signed HTTPS support for the AmneziaWG Easy admin panel.
- Bot-generated NekoBox/sing-box JSON alongside AmneziaWG `.conf` files.

### Changed

- Client recommendations were refreshed for NyameBox/NekoBox usage.

## [1.0.0] - 2026-06-11

First public release of the complete VPN Stack distribution.

### Added

- Docker Compose deployment for AmneziaWG Easy, Xray Reality, and the
  Telegram management bot.
- Interactive `setup.sh` installer with persistent `.env`, WireGuard, and
  Xray configuration.
- AmneziaWG web administration with peer creation, deletion, enable/disable,
  configuration download, and QR codes.
- Per-peer `H1-H4`, `I1-I5`, and `Init_Packet_Delay` configuration.
- Eleven built-in traffic masking profiles with editable values.
- Split-tunnel client routes that preserve access to private LAN networks.
- Telegram management for AmneziaWG peers and VLESS Reality clients.
- Safe Xray client creation with configuration validation and rollback.
- Detailed documentation in Russian, English, and Simplified Chinese.
- Client setup instructions for Windows, macOS, iOS/iPadOS, and Android.

### Operations

- Existing installations can continue tracking the `main` branch.
- The external `vpn-stack-safe-update.sh` workflow remains compatible.
- Runtime state remains outside Git in `.env`, `data/`, and generated
  `xray-config/config.json`.
- Updating to this release does not require resetting VPN keys or peers.

[1.0.0]: https://github.com/sstpnk/vpn-stack/releases/tag/v1.0.0
[1.0.1]: https://github.com/sstpnk/vpn-stack/releases/tag/v1.0.1
[1.1.0]: https://github.com/sstpnk/vpn-stack/releases/tag/v1.1.0
