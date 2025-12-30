#!/bin/bash
# 快速同步脚本 - 从宿主机运行

set -e

echo "开始同步K线数据从MySQL到ClickHouse..."

# 加载环境变量
cd /home/bxgh/microservice-stock/services/get-stockdata
source .env || { echo "错误: 无法加载 .env 文件"; exit 1; }

# 执行Python同步脚本
python3 scripts/sync_kline_to_clickhouse.py --mode full --batch-size 10000

echo "同步完成！"
