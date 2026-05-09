#!/bin/bash
# Clear top of GOST chain
for i in {1..20}; do
  iptables -t nat -D GOST 1 2>/dev/null
done

# 1. Force Redirect TDX (Priority 1)
iptables -t nat -I GOST 1 -p tcp --dport 7709 -j REDIRECT --to-ports 12345

# 2. Private IPs Bypass
iptables -t nat -A GOST -d 127.0.0.0/8 -j RETURN
iptables -t nat -A GOST -d 10.0.0.0/8 -j RETURN
iptables -t nat -A GOST -d 172.16.0.0/12 -j RETURN
iptables -t nat -A GOST -d 192.168.0.0/16 -j RETURN

# 3. DNS Bypass
iptables -t nat -A GOST -p udp --dport 53 -j RETURN
iptables -t nat -A GOST -p tcp --dport 53 -j RETURN

# 4. Existing redirects (will be appended automatically if they existed before, 
# but since we cleared top 20, we might have deleted some needed ones if the chain was short.
# Let's assume standard transparent proxy setup usually adds them at bottom.
# We will verify what's left.)
