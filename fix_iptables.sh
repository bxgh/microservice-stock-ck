#!/bin/bash
# Remove top 15 rules to be safe (we can re-add them)
for i in {1..15}; do
  iptables -t nat -D GOST 1 2>/dev/null
done

# Add Standard Private Ranges RETURN
iptables -t nat -I GOST 1 -d 192.168.0.0/16 -j RETURN
iptables -t nat -I GOST 1 -d 172.16.0.0/12 -j RETURN
iptables -t nat -I GOST 1 -d 10.0.0.0/8 -j RETURN
iptables -t nat -I GOST 1 -d 127.0.0.0/8 -j RETURN

# Add DNS RETURN
iptables -t nat -I GOST 1 -p udp --dport 53 -j RETURN
iptables -t nat -I GOST 1 -p tcp --dport 53 -j RETURN

# Add TDX Bypass (Original Request)
iptables -t nat -I GOST 1 -d 175.6.5.153 -j RETURN
iptables -t nat -I GOST 1 -d 139.9.51.18 -j RETURN
iptables -t nat -I GOST 1 -d 139.159.239.163 -j RETURN
iptables -t nat -I GOST 1 -d 119.147.212.81 -j RETURN
iptables -t nat -I GOST 1 -d 124.71.187.122 -j RETURN
iptables -t nat -I GOST 1 -d 59.36.5.11 -j RETURN

# Add 7709 Forced Redirect (User Request)
iptables -t nat -I GOST 1 -p tcp --dport 7709 -j REDIRECT --to-ports 12345
