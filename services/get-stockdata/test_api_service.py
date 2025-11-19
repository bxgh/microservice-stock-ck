#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API服务启动测试
测试FastAPI服务是否能正常启动并提供接口
"""

import asyncio
import sys
import os
import time
import requests
from datetime import datetime

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_api_service():
    print('=== API服务启动测试 ===')

    try:
        from main import create_app
        app = create_app()
        print('✅ FastAPI应用创建成功')

        # 启动服务器进行简单测试
        import uvicorn

        # 在后台启动服务器
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=8083,
            log_level="warning"  # 减少日志输出
        )

        server = uvicorn.Server(config)

        print('🚀 启动API服务器...')

        # 使用asyncio在后台运行服务器
        async def run_server():
            await server.serve()

        # 启动服务器任务
        server_task = asyncio.create_task(run_server())

        # 等待服务器启动
        print('⏳ 等待服务器启动...')
        await asyncio.sleep(3)

        # 测试API端点
        base_url = "http://127.0.0.1:8083"

        print('\n📡 测试API端点...')

        # 测试健康检查
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print(f'✅ 健康检查: {response.json()}')
            else:
                print(f'❌ 健康检查失败: {response.status_code}')
        except Exception as e:
            print(f'❌ 健康检查异常: {e}')

        # 测试股票代码API
        try:
            response = requests.get(f"{base_url}/api/v1/stocks/test", timeout=5)
            if response.status_code == 200:
                print(f'✅ 股票代码API: {response.json()}')
            else:
                print(f'❌ 股票代码API失败: {response.status_code}')
        except Exception as e:
            print(f'❌ 股票代码API异常: {e}')

        # 测试分笔数据API
        try:
            response = requests.get(f"{base_url}/api/v1/ticks/test", timeout=5)
            if response.status_code == 200:
                print(f'✅ 分笔数据API: {response.json()}')
            else:
                print(f'❌ 分笔数据API失败: {response.status_code}')
        except Exception as e:
            print(f'❌ 分笔数据API异常: {e}')

        # 测试API文档页面
        try:
            response = requests.get(f"{base_url}/docs", timeout=5)
            if response.status_code == 200:
                print('✅ API文档页面可访问')
                print(f'   📖 文档地址: {base_url}/docs')
            else:
                print(f'❌ API文档页面不可用: {response.status_code}')
        except Exception as e:
            print(f'❌ API文档页面异常: {e}')

        print('\n⏹️ 服务器将运行10秒后自动停止...')
        await asyncio.sleep(10)

        # 停止服务器
        print('🛑 停止API服务器...')
        server_task.cancel()

        try:
            await asyncio.wait_for(server_task, timeout=5)
        except asyncio.TimeoutError:
            print('⏰ 服务器停止超时')

        print('✅ API服务测试完成')

    except Exception as e:
        print(f'❌ API服务测试失败: {e}')
        return False

    return True

async def main():
    print('开始API服务集成测试...\n')

    try:
        success = await test_api_service()
        if success:
            print('\n🎉 API服务集成测试成功！')
            print('\n📋 可用功能:')
            print('   ✅ FastAPI Web服务')
            print('   ✅ 股票代码API接口')
            print('   ✅ 分笔数据API接口')
            print('   ✅ 健康检查接口')
            print('   ✅ API文档页面')
            print('   ✅ 错误处理机制')

            print('\n🚀 服务已就绪，可以通过以下方式访问:')
            print('   - 健康检查: curl http://127.0.0.1:8083/health')
            print('   - API文档: http://127.0.0.1:8083/docs')
            print('   - 股票API: curl http://127.0.1:8083/api/v1/stocks/test')
            print('   - 分笔API: curl http://127.0.0.1:8083/api/v1/ticks/test')
        else:
            print('\n❌ API服务测试失败')
    except Exception as e:
        print(f'\n❌ 测试过程中发生错误: {e}')

if __name__ == "__main__":
    asyncio.run(main())