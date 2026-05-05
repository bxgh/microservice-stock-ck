#!/bin/bash
# 重新配置策略路由以支持多网口绑定

# ens32 -> 192.168.151.41 (Metric 300) -> Table 100
ip route flush table 100 2>/dev/null
ip route add 192.168.151.0/24 dev ens32 src 192.168.151.41 table 100
ip route add default via 192.168.151.254 dev ens32 table 100
ip rule add from 192.168.151.41 table 100 2>/dev/null

# ens34 -> 192.168.151.47 (Metric 200) -> Table 101
ip route flush table 101 2>/dev/null
ip route add 192.168.151.0/24 dev ens34 src 192.168.151.47 table 101
ip route add default via 192.168.151.254 dev ens34 table 101
ip rule add from 192.168.151.47 table 101 2>/dev/null

# ens35 -> 192.168.151.49 (Metric 100) -> Table 102
ip route flush table 102 2>/dev/null
ip route add 192.168.151.0/24 dev ens35 src 192.168.151.49 table 102
ip route add default via 192.168.151.254 dev ens35 table 102
ip rule add from 192.168.151.49 table 102 2>/dev/null

echo "✅ Policy Routing Restored."
