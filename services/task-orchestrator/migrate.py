#!/usr/bin/env python3
"""
数据库迁移脚本

执行 migrations 目录下的 SQL 文件
"""

import asyncio
import aiomysql
import sys
from pathlib import Path


async def run_migration(sql_file: str):
    """
    执行迁移SQL文件
    
    Args:
        sql_file: SQL文件路径
    """
    print(f"🔧 执行迁移: {sql_file}")
    
    # 读取SQL文件
    sql_path = Path(sql_file)
    if not sql_path.exists():
        print(f"❌ 文件不存在: {sql_file}")
        return False
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 连接数据库
    try:
        conn = await aiomysql.connect(
            host='127.0.0.1',
            port=36301,
            user='root',
            password='alwaysup@888',
            db='alwaysup'
        )
        print(f"✓ 已连接到数据库 alwaysup")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    
    try:
        async with conn.cursor() as cursor:
            # 分割SQL语句（按分号）
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            
            for i, stmt in enumerate(statements, 1):
                # 跳过注释
                if stmt.startswith('--') or stmt.startswith('/*'):
                    continue
                
                print(f"  执行语句 {i}/{len(statements)}...")
                try:
                    await cursor.execute(stmt)
                    await conn.commit()
                except Exception as e:
                    print(f"  ⚠️  警告: {e}")
            
            print(f"✓ 迁移完成，共执行 {len(statements)} 条语句")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"❌ 执行SQL失败: {e}")
        conn.close()
        return False


async def verify_migration():
    """验证迁移结果"""
    print("\n🔍 验证迁移结果...")
    
    try:
        conn = await aiomysql.connect(
            host='127.0.0.1',
            port=36301,
            user='root',
            password='alwaysup@888',
            db='alwaysup'
        )
        
        async with conn.cursor() as cursor:
            # 检查表是否存在
            await cursor.execute("SHOW TABLES LIKE 'task_execution_logs'")
            result = await cursor.fetchone()
            
            if result:
                print("✓ 表 task_execution_logs 已创建")
                
                # 查看表结构
                await cursor.execute("DESCRIBE task_execution_logs")
                columns = await cursor.fetchall()
                print(f"✓ 表结构: {len(columns)} 个字段")
                
                # 检查视图
                await cursor.execute("SHOW TABLES LIKE 'task_execution_stats'")
                view_result = await cursor.fetchone()
                if view_result:
                    print("✓ 视图 task_execution_stats 已创建")
            else:
                print("❌ 表 task_execution_logs 未找到")
        
        conn.close()
    except Exception as e:
        print(f"❌ 验证失败: {e}")


async def main():
    """主函数"""
    # 迁移文件路径
    migration_file = "services/task-orchestrator/migrations/001_task_logs.sql"
    
    print("=" * 60)
    print("Task Orchestrator 数据库迁移")
    print("=" * 60)
    
    # 执行迁移
    success = await run_migration(migration_file)
    
    if success:
        # 验证结果
        await verify_migration()
        
        print("\n" + "=" * 60)
        print("✅ 迁移成功！")
        print("=" * 60)
        return 0
    else:
        print("\n❌ 迁移失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
