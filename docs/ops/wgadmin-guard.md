# AmneziaWG admin panel port guard

`data/wgadmin-guard.sh` and `data/wgadmin-guard.service` keep the AmneziaWG
admin panel (TCP `51821`) on Nebella reachable only through the reverse proxy on
sagitta. The panel stays available at `https://wg.stpnk.tech`, while a direct
connection to `94.183.188.21:51821` from anywhere else is dropped.

## Why iptables and not ufw

Docker publishes container ports with its own NAT and `FORWARD` rules, which are
evaluated before the `INPUT` chain that ufw uses, so a ufw rule does not protect
a published port. `DOCKER-USER` is the one chain Docker leaves to the operator
and routes every forwarded packet through, so the guard lives there.

## Rules

The script creates the `WGADMIN-GUARD` chain and jumps into it first from
`DOCKER-USER`:

| Rule (IPv4) | Purpose |
| --- | --- |
| `-s 45.39.255.9 -p tcp --dport 51821 -j RETURN` | Let the Caddy host proxy `wg.stpnk.tech` through to the panel |
| `-s 172.16.0.0/12 -p tcp --dport 51821 -j RETURN` | Let the containers talk to the panel API (`https://wg-easy:51821`) |
| `-p tcp --dport 51821 -j DROP` | Drop every other source |

The IPv6 chain mirrors it with `fe80::/10` and `fd00::/8` allowed, because the
host has a global IPv6 address and Docker publishes the port on `[::]` as well.

Only TCP `51821` is filtered. `51820/udp` (the tunnel) and `443/tcp` (Xray) keep
their previous exposure.

## Install

The guard is host configuration, not part of `docker compose`:

```bash
install -m 0755 data/wgadmin-guard.sh /usr/local/sbin/wgadmin-guard.sh
install -m 0644 data/wgadmin-guard.service /etc/systemd/system/wgadmin-guard.service
systemctl daemon-reload
systemctl enable --now wgadmin-guard.service
```

The unit runs after `docker.service`, because the `DOCKER-USER` chain only
exists once the daemon is up, and `PartOf=docker.service` re-applies the rules
whenever Docker restarts. `RemainAfterExit=yes` keeps the unit active, since
iptables rules do not survive a reboot on their own.

## Verify

```bash
systemctl is-enabled wgadmin-guard.service   # enabled
systemctl is-active wgadmin-guard.service    # active
iptables -S DOCKER-USER
iptables -S WGADMIN-GUARD
iptables -L WGADMIN-GUARD -v -n              # counters: proxy RETURN grows, DROP sees foreign sources
```

From an outside host `curl -k https://94.183.188.21:51821/` must fail, while
`curl -k https://wg.stpnk.tech/` must answer, and the bot must still list peers.

## Change or roll back

Adjust `PROXY_IP`, `PORT` or the Docker ranges in the script, copy it back and
run `systemctl restart wgadmin-guard.service`. The script rebuilds the chain on
every run, so repeated runs never duplicate rules.

```bash
systemctl disable --now wgadmin-guard.service
iptables -D DOCKER-USER -j WGADMIN-GUARD && iptables -F WGADMIN-GUARD && iptables -X WGADMIN-GUARD
ip6tables -D DOCKER-USER -j WGADMIN-GUARD && ip6tables -F WGADMIN-GUARD && ip6tables -X WGADMIN-GUARD
```

## Related

- `data/` stays ignored because it also holds generated WireGuard state, so the
  two guard files are tracked explicitly; adding another file there needs
  `git add -f`.
- `wg.stpnk.tech` itself is defined in the separate `prod-router` repository,
  which owns Caddy on sagitta.
- The files here contain no credentials, only the public proxy address and the
  panel port.
