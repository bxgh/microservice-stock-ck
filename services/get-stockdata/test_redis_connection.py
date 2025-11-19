#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redis连接测试脚本
验证Redis配置和连接状态
"""

import sys
import os
from datetime import datetime

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_redis_connections():
    """测试多个Redis连接"""
    print("=== Redis连接测试 ===")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    import redis

    # 测试不同的Redis配置
    redis_configs = [
        {"host": "localhost", "port": 6379, "password": "redis123", "db": 0, "name": "项目Redis (6379)"},
        {"host": "localhost", "port": 6380, "db": 0, "name": "测试Redis (6380)"},
        {"host": "127.0.0.1", "port": 6379, "password": "redis123", "db": 0, "name": "IP方式 (6379)"},
        {"host": "127.0.0.1", "port": 6380, "db": 0, "name": "IP方式 (6380)"}
    ]

    successful_connections = []
    failed_connections = []

    for config in redis_configs:
        try:
            redis_params = {
                "host": config["host"],
                "port": config["port"],
                "db": config["db"],
                "socket_connect_timeout": 5,
                "decode_responses": True
            }

            # 添加密码（如果配置中有的话）
            if "password" in config:
                redis_params["password"] = config["password"]

            r = redis.Redis(**redis_params)

            # 测试连接
            r.ping()

            # 测试读写
            test_key = f"test_key_{config['port']}"
            r.set(test_key, f"test_value_{config['port']}")
            value = r.get(test_key)

            # 获取Redis信息
            info = r.info()
            redis_version = info.get('redis_version', 'unknown')
            used_memory = info.get('used_memory_human', 'unknown')

            successful_connections.append({
                "config": config,
                "version": redis_version,
                "memory": used_memory,
                "test_value": value
            })

            print(f"   ✅ {config['name']}: 连接成功")
            print(f"      Redis版本: {redis_version}")
            print(f"      内存使用: {used_memory}")
            print(f"      测试值: {value}")

        except Exception as e:
            failed_connections.append({
                "config": config,
                "error": str(e)
            })
            print(f"   ❌ {config['name']}: 连接失败 - {e}")

    # 总结
    print(f"\n📊 连接测试总结:")
    print(f"   ✅ 成功连接: {len(successful_connections)}")
    print(f"   ❌ 失败连接: {len(failed_connections)}")

    if successful_connections:
        print(f"\n🎯 可用的Redis配置:")
        for conn in successful_connections:
            config = conn["config"]
            print(f"   • {config['name']}: {config['host']}:{config['port']}")
            print(f"     建议: REDIS_HOST='{config['host']}', REDIS_PORT={config['port']}")

    if failed_connections:
        print(f"\n⚠️ 失败的连接:")
        for conn in failed_connections:
            config = conn["config"]
            print(f"   • {config['name']}: {conn['error']}")

    return len(successful_connections) > 0

def test_service_with_redis():
    """测试服务与Redis的集成"""
    print(f"\n=== 服务Redis集成测试 ===")

    try:
        # 测试股票代码客户端
        from services.stock_code_client import stock_client_instance

        # 测试缓存功能
        if hasattr(stock_client_instance, 'cache_client') and stock_client_instance.cache_client:
            print("   ✅ 股票代码客户端已连接Redis")
        else:
            print("   ⚠️ 股票代码客户端使用内存缓存")

        # 测试策略引擎
        from services.guaranteed_success_strategy import guaranteed_strategy_instance
        print("   ✅ 策略引擎初始化成功")

        return True

    except Exception as e:
        print(f"   ❌ 服务集成测试失败: {e}")
        return False

def generate_redis_config_suggestions():
    """生成Redis配置建议"""
    print(f"\n💡 Redis配置建议:")

    print(f"\n1. 环境变量配置:")
    print(f"   export REDIS_HOST='localhost'")
    print(f"   export REDIS_PORT=6380")
    print(f"   export REDIS_DB=0")

    print(f"\n2. Docker运行Redis (无密码):")
    print(f"   docker run -d --name redis-for-stock \\")
    print(f"     -p 6380:6379 \\")
    print(f"     redis:7-alpine \\")
    print(f"     redis-server --save '' --appendonly no")

    print(f"\n3. docker-compose配置:")
    print(f"   redis:")
    print(f"     image: redis:7-alpine")
    print(f"     ports:")
    print(f"       - '6380:6379'")
    print(f"     command: redis-server --save '' --appendonly no")

    print(f"\n4. Python连接示例:")
    print(f"   import redis")
    print(f"   r = redis.Redis(host='localhost', port=6380, db=0)")

def main():
    """主函数"""
    print("🔍 开始Redis连接诊断")

    # 运行连接测试
    connection_success = test_redis_connections()

    # 运行服务集成测试
    service_success = test_service_with_redis()

    # 生成配置建议
    generate_redis_config_suggestions()

    # 最终结果
    print(f"\n{'='*60}")
    print(f"📋 诊断结果")
    print(f"{'='*60}")

    if connection_success and service_success:
        print(f"🎉 Redis配置成功！系统可以正常使用Redis缓存。")
        return True
    elif connection_success:
        print(f"⚠️ Redis连接成功，但服务集成需要配置。")
        print(f"请设置环境变量 REDIS_HOST=localhost REDIS_PORT=6380")
        return False
    else:
        print(f"❌ Redis连接失败，请检查Redis服务状态。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)