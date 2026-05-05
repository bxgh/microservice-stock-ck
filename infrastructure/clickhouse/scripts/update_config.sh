#!/bin/bash

# update_config.sh
# 一键更新配置并重启集群（简化运维）

set -e

if [ $# -eq 0 ]; then
    echo "用法: $0 <配置文件名>"
    echo "示例: $0 users.xml"
    echo "      $0 config.xml"
    exit 1
fi

CONFIG_FILE=$1
CONFIG_PATH="infrastructure/clickhouse/config/$CONFIG_FILE"
SSH_OPTS="-o StrictHostKeyChecking=no -o BatchMode=yes"

# 验证配置文件存在
if [ ! -f "$CONFIG_PATH" ]; then
    echo "错误: 配置文件不存在: $CONFIG_PATH"
    exit 1
fi

echo "===== ClickHouse 配置更新工具 ====="
echo "目标文件: $CONFIG_FILE"
echo

# 1. 分发配置
echo "[1/3] 分发配置到远程节点..."
scp $SSH_OPTS "$CONFIG_PATH" bxgh@192.168.151.58:~/microservice-stock-deploy/clickhouse/config/
scp $SSH_OPTS "$CONFIG_PATH" bxgh@192.168.151.111:~/microservice-stock-deploy/clickhouse/config/
echo "✓ 配置已分发"

# 2. 重启所有节点
echo ""
echo "[2/3] 重启集群节点..."
docker restart microservice-stock-clickhouse
ssh $SSH_OPTS bxgh@192.168.151.58 "docker restart microservice-stock-clickhouse"
ssh $SSH_OPTS bxgh@192.168.151.111 "docker restart microservice-stock-clickhouse"
echo "✓ 所有节点已重启"

# 3. 等待健康检查
echo ""
echo "[3/3] 等待集群恢复..."
sleep 15

# 验证 Keeper 状态
KEEPER_STATE=$(echo mntr | nc -w 2 127.0.0.1 9181 | grep zk_server_state | awk '{print $2}')
echo "Keeper 状态: $KEEPER_STATE"

if [[ "$KEEPER_STATE" == "leader" || "$KEEPER_STATE" == "follower" ]]; then
    echo ""
    echo "===== 配置更新成功 ====="
else
    echo ""
    echo "警告: Keeper 状态异常，请手动检查"
fi
