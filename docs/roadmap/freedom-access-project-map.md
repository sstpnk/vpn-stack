# Freedom Access Project Map

Date: 2026-09-14

This document records the current project map and the AmneziaWG compatibility
contract before adding server-generated AmneziaWG 3.1 configs.

## Scope

Freedom Access is the working name for the connected set of projects:

| Project | Local path | Remote | Role |
| --- | --- | --- | --- |
| `vpn-stack` | `C:\Users\Sergey\Code\vpn-stack` | `https://github.com/sstpnk/vpn-stack` | Server distribution: Docker Compose, Telegram bot, Xray Reality, bundled admin UI. |
| `awg-easy` | `C:\Users\Sergey\Code\vpn-stack\awg-easy` | based on `https://github.com/spcfox/amnezia-wg-easy` | Current admin UI fork for peer creation, QR/config download, masking presets, and internal API. |
| `freedom-cat` | `C:\Users\Sergey\Code\freedom-cat` | `https://github.com/sstpnk/freedom-cat` | Android client fork with WireGuard and AmneziaWG import/runtime support. |
| `sing-box` fork | cloned next to `freedom-cat` by `buildScript/lib/core/get_source.sh` | `https://github.com/sstpnk/sing-box` | Client protocol core consumed by FreedomCat `libcore`. |
| `vpn-stack-landing` | `C:\Users\Sergey\Code\vpn-stack-landing` | `https://github.com/sstpnk/vpn-stack-landing` | Public instruction/landing site for the stack and client. |
| `prod-router` | `C:\Users\Sergey\Code\prod-router` | `https://github.com/sstpnk/prod-router` | Sagitta Caddy router for `access.stpnk.tech`, `wg.stpnk.tech`, and other production routes. |

## Deployment Map

| Host/domain | Owner repo | Current role | Verification target |
| --- | --- | --- | --- |
| Nebella, currently reachable as `94.183.188.21` in prior notes | `vpn-stack` | Runs `vpn-awg-easy`, `vpn-xray`, and `vpn-bot`. | Re-audit live containers and volumes before deploy. |
| `wg.stpnk.tech` | `prod-router` | Caddy on Sagitta proxies browser HTTPS to Nebella AWG admin HTTPS on `94.183.188.21:51821`. | Caddy config validation, HTTPS response, admin UI reachability. |
| Sagitta | `vpn-stack-landing`, `prod-router` | Hosts the static landing container and public Caddy router. | `access.stpnk.tech` returns the built landing site. |
| `access.stpnk.tech` | `vpn-stack-landing` via `prod-router` | Public landing/instructions. | Browser check and static asset cache behavior. |

Before any production change, back up `vpn-stack` data: `.env`,
`data/wg-easy`, and `xray-config/config.json`.

## Current Server-Side AWG Contract

`vpn-stack` currently generates AmneziaWG configs through the bundled
`awg-easy` fork.

Supported server/interface fields:

| Field | Server `wg0.conf` | Client `.conf` | Notes |
| --- | --- | --- | --- |
| `Jc`, `Jmin`, `Jmax` | yes | yes | Stored on first server config creation. |
| `S1`, `S2` | yes | yes | Server/client defaults are exposed via `.env` and Compose. |
| `S3`, `S4` | no | no | Required by the 3.x model. |
| `H1`-`H4` | yes | yes | Can be per-peer in generated client configs. |
| `I1`-`I5` | no | yes | Stored as global env defaults or per-peer masking profile; not written to server `wg0.conf`. |
| `Init_Packet_Delay` | no | optional | Per-peer custom field only. |
| `HeaderProtectionKey` | no | no | Required to enable header protection. |
| `ContentPaddingAddition` | no | no | 3.x endpoint setting. |
| `RekeyAfterTime` | no | no | 3.x timing range. |
| `RekeyTimeout` | no | no | 3.x timing range. |
| `RejectAfterTime` | no | no | 3.x timing range. |
| `KeepaliveTimeout` | no | no | 3.x timing range. |
| `MaxHandshakeAttempts` | no | no | 3.x timing range/count. |
| `RandomTrailers` | no | no | 3.1 packet trailer control. |
| `DisableCookies` | no | no | 3.1 Cookie Reply control. |
| ranged `PersistentKeepalive` | no | no | Current server uses an integer default of `25`. |

The next server-side change should add these missing fields without changing
legacy behavior unless a 3.1 mode is explicitly enabled.

## Current Client-Side AWG Contract

FreedomCat already has a wider AmneziaWG surface than the server generator:

| Area | Current evidence | Compatibility impact |
| --- | --- | --- |
| Runtime dependency | `libcore/go.mod` pins `github.com/amnezia-vpn/amneziawg-go/v3 v3.1.20260828`. | Client runtime is already on the 3.1 line. |
| sing-box source | `buildScript/lib/core/get_source.sh` clones `sstpnk/sing-box` and checks out `COMMIT_SING_BOX=45ec5dcaf6ab0edcc0822d11c7315d8b3f90e356`. | FreedomCat depends on the forked sing-box source next to the Android repo. |
| Import parser | `WireGuardFmt.kt` parses `S3`, `S4`, `HeaderProtectionKey`, `ContentPaddingAddition`, timing fields, `RandomTrailers`, `DisableCookies`, and ranged `PersistentKeepalive`. | Server-generated 3.1 configs should import without client parser work. |
| UI | `wireguard_preferences.xml` and `WireGuardSettingsActivity.kt` expose the Amnezia 3.1 fields. | Manual editing exists on the client side. |
| Tests | `WireGuardFmtTest.kt` includes an AWG 3.1 config fixture with the full field set. | Server contract tests should reuse the same field names and value shapes. |

## Primary AWG 3.1 Rules To Preserve

The official AmneziaWG documentation and upstream source define these rules:

| Rule | Source-backed requirement |
| --- | --- |
| Header protection needs `HeaderProtectionKey` and `S1`-`S4` large enough for nonce material. |
| With header protection, keep `H1=1`, `H2=2`, `H3=3`, and `H4=4` to disable custom packet headers and hide message type through header protection. |
| `ContentPaddingAddition`, `RekeyAfterTime`, `RekeyTimeout`, `RejectAfterTime`, `KeepaliveTimeout`, and `MaxHandshakeAttempts` accept a single value or range. |
| `RandomTrailers` and `DisableCookies` accept `on` or `off`. |
| A value of `0`, `off`, or `0-0` disables the corresponding 3.x mechanism. |
| `RandomTrailers` must be treated as a shared server/client compatibility setting. |

Primary references:

- Amnezia docs: `https://docs.amnezia.org/documentation/amnezia-wg/`
- `amneziawg-go` UAPI: `https://github.com/amnezia-vpn/amneziawg-go/blob/master/device/uapi.go`
- `amneziawg-go` README: `https://github.com/amnezia-vpn/amneziawg-go`
- `wg-easy` Amnezia config notes: `https://github.com/wg-easy/wg-easy/blob/master/docs/content/advanced/config/amnezia.md`

## Proposed Repository Boundaries

Keep `vpn-stack` as the distribution repo. It should pin and assemble owned
components, not hide their source responsibilities.

Promote `awg-easy` to a maintained fork component. It already carries local
product changes: HTTPS admin API, QR endpoint, traffic UI, per-peer masking
presets, generated config naming, split-tunnel defaults, MTU defaults, and
keepalive defaults.

Keep `freedom-cat` as the reference Android client. Its test fixtures should
drive the server-generated config contract.

Treat `amneziawg-go`, `amneziawg-tools`, and `sstpnk/sing-box` as a pinned
protocol set. Fork or source-build them when the runtime needs a patch; until
then, record exact versions and revisions.

Keep `vpn-stack-landing` and `prod-router` separate. The landing explains the
product and migration path; the router owns public domains and TLS.

## First Code Contract

The first code change in `vpn-stack` should be intentionally small:

1. Add an explicit AWG protocol mode setting, defaulting to legacy behavior.
2. Add environment/config defaults for the AWG 3.1 fields, but write them only
   when 3.1 mode is enabled.
3. Generate a stable 32-byte base64 `HeaderProtectionKey` when 3.1 mode is first
   enabled and no stored key exists.
4. Store 3.1 server fields in `wg0.json` so existing servers keep their chosen
   contract after restart.
5. Emit matching 3.1 fields in both server and client configs.
6. Keep legacy configs byte-compatible enough that old clients do not see
   unknown 3.x fields.
7. Add tests for legacy omission, 3.1 emission, persisted key behavior, and
   FreedomCat-compatible field names.

## Open Questions

1. Should `awg-easy` move to its own GitHub repository before or after the first
   AWG 3.1 implementation commit?
2. Should 3.1 defaults enable only header protection, or also
   `RandomTrailers=on`?
3. Should `DisableCookies` default to `off` for safer DoS behavior or `on` for
   stronger active-probing resistance?
4. Should the Telegram bot's generated NekoBox JSON include AWG 3.1 fields in
   the first contract change, or follow after `.conf` support lands?

## Working Tree Notes

At the time of this audit, `vpn-stack` is clean before this document is added.
`freedom-cat` is clean when read with `safe.directory`. `vpn-stack-landing` is
clean. `prod-router` has an unrelated modified `.gitignore`; do not include it
in this work.
