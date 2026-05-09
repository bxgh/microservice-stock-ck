#!/bin/bash
# Server 41 三网卡配置部署脚本
# 执行时间: 2026-01-08

set -e

echo "=========================================="
echo "Server 41 三网卡配置部署"
echo "=========================================="

# 1. 备份现有配置
echo "[1/5] 备份现有 Netplan 配置..."
if [ -f /etc/netplan/50-cloud-init.yaml ]; then
    sudo cp /etc/netplan/50-cloud-init.yaml /etc/netplan/50-cloud-init.yaml.bak.$(date +%Y%m%d_%H%M%S)
fi

# 2. 部署新配置
echo "[2/5] 部署三网卡配置文件..."
sudo cp 60-triple-nic-config-41.yaml /etc/netplan/60-triple-nic-config.yaml
sudo chown root:root /etc/netplan/60-triple-nic-config.yaml
sudo chmod 600 /etc/netplan/60-triple-nic-config.yaml

# 3. 验证配置语法
echo "[3/5] 验证 Netplan 配置语法..."
sudo netplan generate

# 4. 应用配置
echo "[4/5] 应用网络配置（可能会短暂断网）..."
sudo netplan apply

# 5. 等待网络稳定
echo "[5/5] 等待网络接口稳定..."
sleep 3

echo ""
echo "=========================================="
echo "✅ 配置部署完成！"
echo "=========================================="
echo ""
echo "请执行以下命令验证配置："
echo "  ip addr show"
echo "  ip route show"
echo ""
