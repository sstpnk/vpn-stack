#!/bin/bash
# Keep the AmneziaWG admin panel (TCP 51821) reachable only through the reverse
# proxy on sagitta (45.39.255.9) and from the Docker networks. Everything else
# is dropped, so 94.183.188.21:51821 stays closed to the internet while
# https://wg.stpnk.tech keeps working. Re-run safe: the chain is rebuilt.
set -eu

PORT=51821
PROXY_IP=45.39.255.9
CHAIN=WGADMIN-GUARD

iptables -N DOCKER-USER 2>/dev/null || true
ip6tables -N DOCKER-USER 2>/dev/null || true

iptables -N "$CHAIN" 2>/dev/null || true
iptables -F "$CHAIN"
iptables -A "$CHAIN" -s "$PROXY_IP" -p tcp --dport "$PORT" -j RETURN
iptables -A "$CHAIN" -s 172.16.0.0/12 -p tcp --dport "$PORT" -j RETURN
iptables -A "$CHAIN" -p tcp --dport "$PORT" -j DROP
iptables -C DOCKER-USER -j "$CHAIN" 2>/dev/null || iptables -I DOCKER-USER 1 -j "$CHAIN"

ip6tables -N "$CHAIN" 2>/dev/null || true
ip6tables -F "$CHAIN"
ip6tables -A "$CHAIN" -s fe80::/10 -p tcp --dport "$PORT" -j RETURN
ip6tables -A "$CHAIN" -s fd00::/8 -p tcp --dport "$PORT" -j RETURN
ip6tables -A "$CHAIN" -p tcp --dport "$PORT" -j DROP
ip6tables -C DOCKER-USER -j "$CHAIN" 2>/dev/null || ip6tables -I DOCKER-USER 1 -j "$CHAIN"
