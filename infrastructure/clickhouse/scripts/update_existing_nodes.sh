#!/bin/bash

# 41/58服务器配置更新脚本
# 用途: 更新现有节点的配置以支持3节点模式
# 使用方法: 
#   在41服务器上: sudo bash update_existing_nodes.sh 41
#   在58服务器上: sudo bash update_existing_nodes.sh 58

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 当前服务器ID
CURRENT_SERVER=${1:-""}

if [ "$CURRENT_SERVER" != "41" ] && [ "$CURRENT_SERVER" != "58" ]; then
    echo -e "${RED}错误: 请指定服务器ID (41 或 58)${NC}"
    echo -e "使用方法: sudo bash $0 [41|58]"
    exit 1
fi

# 检查是否为root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请使用 root 权限运行此脚本${NC}"
    echo -e "使用方法: sudo bash $0 $CURRENT_SERVER"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Server ${CURRENT_SERVER} 配置更新 (3节点模式)${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 配置文件目录
CONFIG_DIR="/etc/clickhouse-server/config.d"
BACKUP_DIR="/backup/clickhouse-config-$(date +%Y%m%d-%H%M%S)"

# 设置服务器特定参数
if [ "$CURRENT_SERVER" == "41" ]; then
    SERVER_ID="1"
    REPLICA_NAME="server41"
    INTERSERVER_IP="192.168.151.41"
else
    SERVER_ID="2"
    REPLICA_NAME="server58"
    INTERSERVER_IP="192.168.151.58"
fi

# 创建备份
echo -e "${BLUE}[1/4] 备份现有配置${NC}"
mkdir -p "$BACKUP_DIR"
cp -r "$CONFIG_DIR"/* "$BACKUP_DIR/"
echo -e "${GREEN}✓${NC} 备份完成: $BACKUP_DIR\n"

# 更新 Keeper 配置
echo -e "${BLUE}[2/4] 更新 Keeper 配置${NC}"
cat > "$CONFIG_DIR/keeper_config.xml" << EOF
<?xml version="1.0"?>
<clickhouse>
    <keeper_server>
        <tcp_port>9181</tcp_port>
        <server_id>${SERVER_ID}</server_id>
        <log_storage_path>/var/lib/clickhouse/coordination/log</log_storage_path>
        <snapshot_storage_path>/var/lib/clickhouse/coordination/snapshots</snapshot_storage_path>

        <coordination_settings>
            <operation_timeout_ms>10000</operation_timeout_ms>
            <session_timeout_ms>30000</session_timeout_ms>
            <raft_logs_level>warning</raft_logs_level>
        </coordination_settings>

        <raft_configuration>
            <server>
                <id>1</id>
                <hostname>192.168.151.41</hostname>
                <port>9234</port>
            </server>
            <server>
                <id>2</id>
                <hostname>192.168.151.58</hostname>
                <port>9234</port>
            </server>
            <server>
                <id>3</id>
                <hostname>192.168.151.111</hostname>
                <port>9234</port>
            </server>
        </raft_configuration>
    </keeper_server>
</clickhouse>
EOF

echo -e "${GREEN}✓${NC} Keeper 配置已更新 (server_id=${SERVER_ID})\n"

# 更新复制配置
echo -e "${BLUE}[3/4] 更新复制配置${NC}"
cat > "$CONFIG_DIR/replication_config.xml" << EOF
<?xml version="1.0"?>
<clickhouse>
    <!-- 宏定义 - 用于复制表路径 -->
    <macros>
        <shard>01</shard>
        <replica>${REPLICA_NAME}</replica>
    </macros>

    <!-- 连接到 ClickHouse Keeper 集群 -->
    <zookeeper>
        <node>
            <host>192.168.151.41</host>
            <port>9181</port>
        </node>
        <node>
            <host>192.168.151.58</host>
            <port>9181</port>
        </node>
        <node>
            <host>192.168.151.111</host>
            <port>9181</port>
        </node>
        <session_timeout_ms>30000</session_timeout_ms>
    </zookeeper>

    <!-- 集群配置 -->
    <remote_servers>
        <stock_cluster>
            <shard>
                <internal_replication>true</internal_replication>
                <replica>
                    <host>192.168.151.41</host>
                    <port>9000</port>
                </replica>
                <replica>
                    <host>192.168.151.58</host>
                    <port>9000</port>
                </replica>
                <replica>
                    <host>192.168.151.111</host>
                    <port>9000</port>
                </replica>
            </shard>
        </stock_cluster>
    </remote_servers>

    <!-- 允许远程连接 -->
    <listen_host>0.0.0.0</listen_host>
    
    <!-- 关键：告诉其他副本如何连接我 -->
    <interserver_http_host>${INTERSERVER_IP}</interserver_http_host>
</clickhouse>
EOF

echo -e "${GREEN}✓${NC} 复制配置已更新 (replica=${REPLICA_NAME})\n"

# 设置权限
echo -e "${BLUE}[4/4] 设置文件权限${NC}"
chown clickhouse:clickhouse "$CONFIG_DIR"/*.xml
chmod 644 "$CONFIG_DIR"/*.xml
echo -e "${GREEN}✓${NC} 权限设置完成\n"

# 验证配置
echo -e "${BLUE}验证配置文件${NC}"
ls -lh "$CONFIG_DIR"/keeper_config.xml "$CONFIG_DIR"/replication_config.xml

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Server ${CURRENT_SERVER} 配置更新完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "\n${YELLOW}⚠ 重要提示:${NC}"
echo -e "${RED}配置已更新，但尚未生效！${NC}\n"
echo -e "${YELLOW}下一步操作（严格按顺序）:${NC}"
echo -e "1. 确认当前 Keeper 状态:"
echo -e "   ${BLUE}echo 'mntr' | nc localhost 9181 | grep zk_server_state${NC}"
echo -e "\n2. 如果当前是 ${RED}Leader${NC}，请${RED}最后重启${NC}"
echo -e "   如果当前是 ${GREEN}Follower${NC}，可以先重启\n"
echo -e "3. 重启服务:"
echo -e "   ${BLUE}systemctl restart clickhouse-server${NC}"
echo -e "\n4. 验证重启成功:"
echo -e "   ${BLUE}systemctl status clickhouse-server${NC}"
echo -e "   ${BLUE}echo 'mntr' | nc localhost 9181${NC}\n"

echo -e "${YELLOW}备份位置: $BACKUP_DIR${NC}\n"
