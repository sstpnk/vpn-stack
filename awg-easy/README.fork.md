# vpn-stack AmneziaWG Easy fork

This directory is based on
[spcfox/amnezia-wg-easy](https://github.com/spcfox/amnezia-wg-easy), upstream
commit `235caf1`.

Local changes:

- Add configurable `I1` through `I5` values to generated client configs.
- Add explanatory comments for transport masking, dynamic headers, and CPS
  packets to downloaded and QR-generated client configs.
- Use AmneziaWG 2.0-compatible CPS defaults and non-overlapping `H1` through
  `H4` ranges for newly initialized servers.
- Default client MTU to `1280`.
- Default client persistent keepalive to `25` seconds.
- Default `AllowedIPs` to public IPv4 routes that exclude RFC1918 private
  networks.
- Keep all values configurable through environment variables.
- Restore the missing Web UI action that opens the existing client QR endpoint.

The upstream project is licensed under GPL-3.0. See `LICENSE`.
