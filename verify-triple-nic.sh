#!/bin/bash
# Server 58 三网卡配置验证脚本

echo "=========================================="
echo "Server 58 三网卡配置验证"
echo "=========================================="
echo ""

# 1. 检查网卡状态
echo "📡 [1/4] 网卡状态检查"
echo "----------------------------------------"
for nic in ens32 ens34 ens35; do
    status=$(ip link show $nic 2>/dev/null | grep -oP 'state \K\w+' || echo "NOT_FOUND")
    ip_addr=$(ip addr show $nic 2>/dev/null | grep -oP 'inet \K[\d.]+' || echo "未配置")
    mac=$(ip link show $nic 2>/dev/null | grep -oP 'link/ether \K[\da-f:]+' || echo "N/A")
    
    if [ "$status" = "UP" ]; then
        echo "✅ $nic: $status | IP: $ip_addr | MAC: $mac"
    elif [ "$status" = "DOWN" ]; then
        echo "⚠️  $nic: $status | IP: $ip_addr | MAC: $mac"
    else
        echo "❌ $nic: 未找到"
    fi
done
echo ""

# 2. 检查 IP 分配
echo "🌐 [2/4] IP 地址分配检查"
echo "----------------------------------------"
expected_ips=("192.168.151.58" "192.168.151.55" "192.168.151.56")
nics=("ens32" "ens34" "ens35")

for i in {0..2}; do
    nic=${nics[$i]}
    expected=${expected_ips[$i]}
    actual=$(ip addr show $nic 2>/dev/null | grep -oP 'inet \K[\d.]+' || echo "")
    
    if [ "$actual" = "$expected" ]; then
        echo "✅ $nic: $actual (符合预期)"
    else
        echo "❌ $nic: 实际=$actual, 预期=$expected"
    fi
done
echo ""

# 3. 检查路由策略
echo "🛣️  [3/4] 路由策略检查"
echo "----------------------------------------"
echo "默认路由 (按 Metric 优先级):"
ip route show | grep default | sort -k9 -n
echo ""
echo "集群节点路由 (应走 ens32):"
ip route show | grep -E '192.168.151.(41|111)' || echo "⚠️  未找到集群节点路由"
echo ""
echo "代理网关路由 (应走 ens34):"
ip route show | grep '192.168.151.18' || echo "⚠️  未找到代理网关路由"
echo ""

# 4. 连通性测试
echo "🔌 [4/4] 网络连通性测试"
echo "----------------------------------------"
test_targets=("192.168.151.254" "192.168.151.41" "192.168.151.111")
test_names=("网关" "Server 41" "Server 111")

for i in {0..2}; do
    target=${test_targets[$i]}
    name=${test_names[$i]}
    if ping -c 1 -W 2 $target &>/dev/null; then
        echo "✅ $name ($target): 可达"
    else
        echo "❌ $name ($target): 不可达"
    fi
done
echo ""

echo "=========================================="
echo "验证完成！"
echo "=========================================="
