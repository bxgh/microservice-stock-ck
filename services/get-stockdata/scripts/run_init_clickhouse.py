#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ClickHouse 数据库初始化脚本
读取 SQL 文件并执行，创建必要的表结构
"""

import os
import sys
from clickhouse_driver import Client

# SQL 文件路径
SQL_FILE = os.path.join(
    os.path.dirname(__file__),
    'init_clickhouse.sql'
)

# ClickHouse 连接配置
CLICKHOUSE_CONFIG = {
    'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
    'port': int(os.getenv('CLICKHOUSE_PORT', 9000)),
    'user': os.getenv('CLICKHOUSE_USER', 'default'),
    'password': os.getenv('CLICKHOUSE_PASSWORD', ''),
}


def read_sql_file(filepath: str) -> list:
    """
    读取 SQL 文件并拆分为独立语句
    
    Args:
        filepath: SQL 文件路径
        
    Returns:
        SQL 语句列表
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按分号拆分语句
    statements = []
    for statement in content.split(';'):
        statement = statement.strip()
        # 过滤注释和空行
        if statement and not statement.startswith('--'):
            statements.append(statement)
    
    return statements


def execute_sql_statements(client: Client, statements: list):
    """
    执行 SQL 语句列表
    
    Args:
        client: ClickHouse 客户端
        statements: SQL 语句列表
    """
    for i, statement in enumerate(statements, 1):
        try:
            # 跳过纯注释语句
            if all(line.strip().startswith('--') or not line.strip() 
                   for line in statement.split('\n')):
                continue
                
            print(f"[{i}/{len(statements)}] 执行SQL...")
            result = client.execute(statement)
            
            # 如果有返回结果，打印
            if result:
                for row in result:
                    print(f"  {row}")
                    
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            print(f"   语句: {statement[:100]}...")
            # 不中断，继续执行下一条


def main():
    """主函数"""
    print("=" * 50)
    print("ClickHouse 数据库初始化")
    print("=" * 50)
    
    # 检查 SQL 文件是否存在
    if not os.path.exists(SQL_FILE):
        print(f"❌ SQL 文件不存在: {SQL_FILE}")
        sys.exit(1)
    
    # 连接 ClickHouse
    try:
        print(f"\n📡 连接 ClickHouse: {CLICKHOUSE_CONFIG['host']}:{CLICKHOUSE_CONFIG['port']}")
        client = Client(**CLICKHOUSE_CONFIG)
        print("✅ 连接成功\n")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        sys.exit(1)
    
    # 读取 SQL 文件
    print(f"📄 读取 SQL 文件: {SQL_FILE}")
    statements = read_sql_file(SQL_FILE)
    print(f"   找到 {len(statements)} 条SQL语句\n")
    
    # 执行 SQL
    print("🚀 开始执行SQL...")
    execute_sql_statements(client, statements)
    
    # 断开连接
    client.disconnect()
    
    print("\n" + "=" * 50)
    print("✅ 初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
