# Public Host Configuration Design

## Goal

Allow deployments to use a DNS name as the public VPN endpoint so future VPS IP changes only require DNS updates and do not require regenerating server-side defaults.

## Scope

The public repository must support a generic domain-or-IP setting. It must not contain any private deployment value such as a personal domain.

## Design

Introduce `PUBLIC_HOST` as the preferred public address setting. It may contain either a DNS name or an IPv4 address. Existing `WG_HOST` remains supported for backward compatibility because AmneziaWG Easy already uses it to build client `Endpoint` values and existing deployments may already have it in `.env`.

`setup.sh` will ask for "Public server host (domain or IP)" instead of "Server IP address". For new `.env` files it will write:

- `PUBLIC_HOST=<entered value>`
- `WG_HOST=<entered value>`
- `XRAY_PUBLIC_HOST=<entered value>`

This keeps AmneziaWG and Xray links aligned without relying on Docker Compose nested variable expansion.

The Xray bot will resolve the public host in this order:

1. `XRAY_PUBLIC_HOST`
2. `PUBLIC_HOST`
3. `WG_HOST`

This preserves existing behavior while making the new shared setting useful for Xray-specific deployments too.

## Documentation

README examples and troubleshooting should describe the setting as a public host, not only as an IP address. The docs should recommend using a DNS name and updating DNS when the VPS IP changes.

## Testing

Add or update bot unit coverage so `PUBLIC_HOST` is used when `XRAY_PUBLIC_HOST` is unset. Run the existing Xray manager test module after implementation.
