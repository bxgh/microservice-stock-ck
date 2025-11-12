#!/usr/bin/env python3
"""
服务发现示例代码
演示如何使用服务注册发现功能进行服务间通信
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from registry import ServiceClient, ServiceClientFactory, get_service_registry

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceDiscoveryExample:
    """服务发现示例类"""

    def __init__(self):
        self.consul_url = os.getenv("CONSUL_URL", "http://localhost:8500")

    async def basic_service_discovery(self):
        """基础服务发现示例"""
        logger.info("=== 基础服务发现示例 ===")

        try:
            registry = await get_service_registry()
            await registry.start()

            # 发现所有服务
            services = await registry.list_services()
            logger.info(f"发现的服务: {list(services.keys())}")

            # 查找特定服务实例
            if 'task-scheduler' in services:
                instances = services['task-scheduler']
                logger.info(f"TaskScheduler 服务实例: {len(instances)} 个")
                for instance in instances:
                    logger.info(f"  - {instance.service_id}: {instance.address}:{instance.port}")

            await registry.stop()

        except Exception as e:
            logger.error(f"基础服务发现失败: {e}")

    async def service_client_example(self):
        """服务客户端示例"""
        logger.info("=== 服务客户端示例 ===")

        try:
            # 创建服务客户端
            client = ServiceClient("task-scheduler")
            await client.start()

            # 发送健康检查请求
            health_response = await client.get("/api/v1/health")
            logger.info(f"健康检查响应: {health_response}")

            # 获取服务根信息
            root_response = await client.get("/")
            logger.info(f"根路径响应: {root_response}")

            await client.stop()

        except Exception as e:
            logger.error(f"服务客户端请求失败: {e}")

    async def load_balanced_client_example(self):
        """负载均衡客户端示例"""
        logger.info("=== 负载均衡客户端示例 ===")

        try:
            # 创建负载均衡客户端
            client = ServiceClientFactory.get_load_balanced_client(
                "task-scheduler",
                strategy="round_robin"
            )

            # 发送多个请求测试负载均衡
            for i in range(3):
                try:
                    response = await client.get("/api/v1/health")
                    logger.info(f"请求 {i+1} 响应: {response.get('service_id', 'unknown')}")
                except Exception as e:
                    logger.warning(f"请求 {i+1} 失败: {e}")

        except Exception as e:
            logger.error(f"负载均衡客户端失败: {e}")

    async def service_registration_example(self):
        """服务注册示例"""
        logger.info("=== 服务注册示例 ===")

        try:
            registry = await get_service_registry()
            await registry.start()

            # 创建示例服务实例
            from registry import ServiceInstance
            example_service = ServiceInstance(
                service_id="example-service-1",
                service_name="example-service",
                address="127.0.0.1",
                port=9999,
                tags=["example", "test"],
                meta={"version": "1.0.0", "description": "示例服务"},
                health_check_url="http://127.0.0.1:9999/health",
                health_check_interval="10s"
            )

            # 注册服务
            success = await registry.register_service(example_service)
            if success:
                logger.info("示例服务注册成功")

                # 发现刚注册的服务
                instances = await registry.discover_service("example-service")
                logger.info(f"发现示例服务实例: {len(instances)} 个")

                # 注销服务
                await registry.deregister_service("example-service-1")
                logger.info("示例服务已注销")

            await registry.stop()

        except Exception as e:
            logger.error(f"服务注册示例失败: {e}")

    async def cross_service_communication_example(self):
        """跨服务通信示例"""
        logger.info("=== 跨服务通信示例 ===")

        try:
            # 模拟其他微服务调用 TaskScheduler
            client = ServiceClient("task-scheduler")

            async with client:
                # 假设有其他服务端点
                # 这里演示如何调用其他微服务的API

                # 1. 获取任务列表
                try:
                    tasks_response = await client.get("/api/v1/tasks")
                    logger.info(f"获取任务列表: {tasks_response}")
                except Exception as e:
                    logger.warning(f"获取任务列表失败: {e}")

                # 2. 创建新任务
                try:
                    task_data = {
                        "name": "示例任务",
                        "task_type": "http_task",
                        "description": "通过服务发现创建的任务",
                        "config": {
                            "url": "https://api.example.com/ping"
                        },
                        "cron_expression": "0 */5 * * *"
                    }

                    create_response = await client.post("/api/v1/tasks", json=task_data)
                    logger.info(f"创建任务响应: {create_response}")
                except Exception as e:
                    logger.warning(f"创建任务失败: {e}")

        except Exception as e:
            logger.error(f"跨服务通信示例失败: {e}")

    async def service_health_monitoring_example(self):
        """服务健康监控示例"""
        logger.info("=== 服务健康监控示例 ===")

        try:
            registry = await get_service_registry()
            await registry.start()

            # 监控服务健康状态
            for i in range(5):
                logger.info(f"--- 健康检查轮次 {i+1} ---")

                # 检查 Consul 连接
                consul_healthy = await registry._check_consul_health()
                logger.info(f"Consul 健康状态: {'正常' if consul_healthy else '异常'}")

                # 检查注册的服务
                services = await registry.list_services()
                for service_name, instances in services.items():
                    logger.info(f"服务 {service_name}: {len(instances)} 个实例")

                await asyncio.sleep(5)

            await registry.stop()

        except Exception as e:
            logger.error(f"服务健康监控失败: {e}")


async def main():
    """主函数"""
    logger.info("🚀 服务发现示例程序启动")

    example = ServiceDiscoveryExample()

    try:
        # 运行各种示例
        await example.basic_service_discovery()
        await asyncio.sleep(1)

        await example.service_registration_example()
        await asyncio.sleep(1)

        await example.service_client_example()
        await asyncio.sleep(1)

        await example.load_balanced_client_example()
        await asyncio.sleep(1)

        await example.cross_service_communication_example()
        await asyncio.sleep(1)

        await example.service_health_monitoring_example()

        logger.info("✅ 所有示例执行完成")

    except KeyboardInterrupt:
        logger.info("🛑 用户中断程序")
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
    finally:
        # 清理资源
        await ServiceClientFactory.close_all()
        logger.info("🧹 资源清理完成")


if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("CONSUL_URL"):
        logger.warning("未设置 CONSUL_URL 环境变量，使用默认值: http://localhost:8500")

    # 运行示例
    asyncio.run(main())