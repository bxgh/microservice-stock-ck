"""
服务发现相关API路由
提供服务注册状态查询、服务列表等功能
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPAuthorizationCredentials

from models.task_models import ApiResponse
from registry import get_service_registry, ServiceInstance
from api.middleware import get_current_user

logger = logging.getLogger(__name__)

# 创建路由器
discovery_router = APIRouter(prefix="/api/v1/discovery", tags=["service-discovery"])


@discovery_router.get("/services", response_model=ApiResponse, summary="获取所有注册的服务")
async def get_all_services(
    registry=Depends(get_service_registry),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    获取所有在 Consul 中注册的服务列表
    """
    try:
        services = await registry.list_services()

        service_list = []
        for service_name, instances in services.items():
            service_info = {
                "name": service_name,
                "instances": len(instances),
                "details": []
            }

            for instance in instances:
                instance_info = {
                    "id": instance.service_id,
                    "address": f"{instance.address}:{instance.port}",
                    "tags": instance.tags,
                    "meta": instance.meta
                }
                service_info["details"].append(instance_info)

            service_list.append(service_info)

        return ApiResponse(
            success=True,
            message="Services retrieved successfully",
            data={
                "total_services": len(services),
                "services": service_list
            }
        )

    except Exception as e:
        logger.error(f"Failed to get services: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@discovery_router.get("/services/{service_name}", response_model=ApiResponse, summary="获取特定服务信息")
async def get_service_info(
    service_name: str,
    tag: Optional[str] = Query(None, description="服务标签过滤"),
    registry=Depends(get_service_registry),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    获取指定服务的详细信息和实例列表
    """
    try:
        instances = await registry.discover_service(service_name, tag)

        if not instances:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

        service_info = {
            "name": service_name,
            "instances": len(instances),
            "tag_filter": tag,
            "instances_list": []
        }

        for instance in instances:
            instance_info = {
                "id": instance.service_id,
                "address": instance.address,
                "port": instance.port,
                "url": f"http://{instance.address}:{instance.port}",
                "tags": instance.tags,
                "meta": instance.meta,
                "health_check": {
                    "url": instance.health_check_url,
                    "interval": instance.health_check_interval,
                    "timeout": instance.health_check_timeout
                }
            }
            service_info["instances_list"].append(instance_info)

        return ApiResponse(
            success=True,
            message=f"Service '{service_name}' retrieved successfully",
            data=service_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service info for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@discovery_router.get("/registry/status", response_model=ApiResponse, summary="获取服务注册状态")
async def get_registry_status(
    registry=Depends(get_service_registry),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    获取当前服务注册状态和 Consul 连接信息
    """
    try:
        # 检查 Consul 连接
        consul_healthy = await registry._check_consul_health()

        # 获取本地服务信息
        local_service_id = getattr(registry, 'local_service_id', None)

        status_data = {
            "consul_url": registry.consul_url,
            "consul_connected": consul_healthy,
            "local_service_id": local_service_id,
            "local_service_registered": local_service_id is not None,
            "heartbeat_task_active": registry.heartbeat_task is not None and not registry.heartbeat_task.done()
        }

        return ApiResponse(
            success=True,
            message="Registry status retrieved successfully",
            data=status_data
        )

    except Exception as e:
        logger.error(f"Failed to get registry status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@discovery_router.post("/test-service-discovery", response_model=ApiResponse, summary="测试服务发现")
async def test_service_discovery(
    target_service: str = Query(..., description="目标服务名称"),
    path: str = Query("/api/v1/health", description="测试路径"),
    registry=Depends(get_service_registry),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    测试服务发现功能，尝试发现并调用目标服务
    """
    try:
        from registry.service_client import ServiceClient

        # 发现服务实例
        instances = await registry.discover_service(target_service)

        if not instances:
            return ApiResponse(
                success=False,
                message=f"No instances found for service: {target_service}",
                data={"service_name": target_service, "instances_found": 0}
            )

        # 选择一个实例进行测试
        instance = instances[0]

        # 创建客户端并发送请求
        async with ServiceClient(target_service) as client:
            try:
                response = await client.get(path)

                return ApiResponse(
                    success=True,
                    message=f"Successfully communicated with {target_service}",
                    data={
                        "target_service": target_service,
                        "target_instance": f"{instance.address}:{instance.port}",
                        "test_path": path,
                        "response": response
                    }
                )
            except Exception as e:
                return ApiResponse(
                    success=False,
                    message=f"Failed to communicate with {target_service}",
                    data={
                        "target_service": target_service,
                        "target_instance": f"{instance.address}:{instance.port}",
                        "test_path": path,
                        "error": str(e)
                    }
                )

    except Exception as e:
        logger.error(f"Service discovery test failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@discovery_router.get("/metrics", response_model=ApiResponse, summary="获取服务发现指标")
async def get_discovery_metrics(
    registry=Depends(get_service_registry),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    获取服务发现相关的指标信息
    """
    try:
        # 获取所有服务
        services = await registry.list_services()

        # 计算指标
        total_services = len(services)
        total_instances = sum(len(instances) for instances in services.values())

        # 按标签分组统计
        tag_stats = {}
        for instances in services.values():
            for instance in instances:
                for tag in instance.tags:
                    tag_stats[tag] = tag_stats.get(tag, 0) + 1

        metrics_data = {
            "total_services": total_services,
            "total_instances": total_instances,
            "average_instances_per_service": round(total_instances / total_services, 2) if total_services > 0 else 0,
            "tag_distribution": tag_stats,
            "services_by_name": {name: len(instances) for name, instances in services.items()}
        }

        return ApiResponse(
            success=True,
            message="Discovery metrics retrieved successfully",
            data=metrics_data
        )

    except Exception as e:
        logger.error(f"Failed to get discovery metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")