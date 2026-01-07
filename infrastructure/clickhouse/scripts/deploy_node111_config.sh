#!/bin/bash

# 111服务器配置文件快速部署脚本
# 用途: 在111服务器上快速部署Keeper和复制配置
# 使用方法: 在111服务器上以root权限执行
#   sudo bash deploy_node111_config.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}111服务器配置文件快速部署${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 检查是否为root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请使用 root 权限运行此脚本${NC}"
    echo -e "使用方法: sudo bash $0"
    exit 1
fi

# 配置文件目录
CONFIG_DIR="/etc/clickhouse-server/config.d"
BACKUP_DIR="/backup/clickhouse-config-$(date +%Y%m%d-%H%M%S)"

# 创建备份目录
echo -e "${BLUE}[1/5] 创建备份目录${NC}"
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}✓${NC} 备份目录: $BACKUP_DIR\n"

# 备份现有配置
echo -e "${BLUE}[2/5] 备份现有配置${NC}"
if [ -d "$CONFIG_DIR" ]; then
    cp -r "$CONFIG_DIR" "$BACKUP_DIR/"
    echo -e "${GREEN}✓${NC} 已备份现有配置到 $BACKUP_DIR\n"
else
    echo -e "${YELLOW}⚠${NC} 配置目录不存在，将创建新目录\n"
    mkdir -p "$CONFIG_DIR"
fi

# 部署 Keeper 配置
echo -e "${BLUE}[3/5] 部署 Keeper 配置${NC}"
cat > "$CONFIG_DIR/keeper_config.xml" << 'EOF'
<?xml version="1.0"?>
<clickhouse>
    <keeper_server>
        <tcp_port>9181</tcp_port>
        <server_id>3</server_id>
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

echo -e "${GREEN}✓${NC} Keeper 配置已部署\n"

# 部署复制配置
echo -e "${BLUE}[4/5] 部署复制配置${NC}"
cat > "$CONFIG_DIR/replication_config.xml" << 'EOF'
<?xml version="1.0"?>
<clickhouse>
    <!-- 宏定义 - 用于复制表路径 -->
    <macros>
        <shard>01</shard>
        <replica>server111</replica>
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
    <interserver_http_host>192.168.151.111</interserver_http_host>
</clickhouse>
EOF

echo -e "${GREEN}✓${NC} 复制配置已部署\n"

# 设置正确的权限
echo -e "${BLUE}[5/5] 设置文件权限${NC}"
chown clickhouse:clickhouse "$CONFIG_DIR"/*.xml
chmod 644 "$CONFIG_DIR"/*.xml
echo -e "${GREEN}✓${NC} 权限设置完成\n"

# 验证配置
echo -e "${BLUE}验证配置文件${NC}"
ls -lh "$CONFIG_DIR"/*.xml

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ 配置部署完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "\n${YELLOW}下一步操作:${NC}"
echo -e "1. 启动 ClickHouse 服务: ${BLUE}systemctl start clickhouse-server${NC}"
echo -e "2. 检查服务状态: ${BLUE}systemctl status clickhouse-server${NC}"
echo -e "3. 查看日志: ${BLUE}tail -f /var/log/clickhouse-server/clickhouse-server.log${NC}"
echo -e "4. 验证 Keeper: ${BLUE}echo 'mntr' | nc localhost 9181${NC}\n"

echo -e "${YELLOW}备份位置: $BACKUP_DIR${NC}\n"
