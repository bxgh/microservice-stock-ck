#!/bin/bash
# Server 41 三网卡配置验证脚本
# 执行时间: 2026-01-08

echo "=========================================="
echo "🔍 Server 41 三网卡配置验证"
echo "=========================================="

# 1. 检查网卡状态
echo "[1/3] 检查网卡状态..."
for nic in ens32 ens34 ens35; do
    status=$(ip link show $nic | grep -o "state [A-Z]*" | awk '{print $2}')
    if [ "$status" == "UP" ]; then
        echo "✅ $nic: UP"
    else
        echo "❌ $nic: $status"
    fi
done

# 2. 检查 IP 地址分配
echo -e "\n[2/3] 检查 IP 地址分配..."
declare -A expected_ips=( ["ens32"]="192.168.151.41" ["ens34"]="192.168.151.47" ["ens35"]="192.168.151.49" )
for nic in "${!expected_ips[@]}"; do
    ip_addr=$(ip addr show $nic | grep "inet " | awk '{print $2}' | cut -d/ -f1)
    if [ "$ip_addr" == "${expected_ips[$nic]}" ]; then
        echo "✅ $nic: $ip_addr"
    else
        echo "❌ $nic: 预期 ${expected_ips[$nic]}, 实际 $ip_addr"
    fi
done

# 3. 检查关键路由
echo -e "\n[3/3] 检查路由策略..."
check_route() {
    local target=$1
    local expected_nic=$2
    local route_info=$(ip route get $target)
    if echo "$route_info" | grep -q "dev $expected_nic"; then
        echo "✅ $target -> $expected_nic"
    else
        echo "❌ $target -> 预期走 $expected_nic, 实际路由 info: $route_info"
    fi
}

check_route "127.0.0.1" "lo"
check_route "192.168.151.58" "ens32"
check_route "192.168.151.111" "ens32"
check_route "192.168.151.18" "ens34"
check_route "8.8.8.8" "ens35"

echo -e "\n=========================================="
echo "✅ 验证完成！"
echo "=========================================="
