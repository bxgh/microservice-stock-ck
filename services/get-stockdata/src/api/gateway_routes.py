# -*- coding: utf-8 -*-
"""
Gateway 监控路由

提供 DataSourceGateway 的监控和统计接口
"""

from fastapi import APIRouter, HTTPException, Request
import logging

router = APIRouter(prefix="/api/v1/gateway", tags=["Data Source Gateway"])
logger = logging.getLogger(__name__)


@router.get("/stats")
async def get_gateway_stats(request: Request):
    """获取 Gateway 统计信息
    
    Returns:
        Gateway 各个 ProviderChain 的统计信息
    """
    try:
        if not hasattr(request.app.state, 'data_source_gateway'):
            raise HTTPException(
                status_code=503,
                detail="DataSourceGateway not initialized"
            )
        
        gateway = request.app.state.data_source_gateway
        stats = gateway.get_stats()
        
        return {
            "success": True,
            "data": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting gateway stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_gateway_health(request: Request):
    """获取 Gateway 健康状态
    
    Returns:
        Gateway 及各个 Provider 的健康状态
    """
    try:
        if not hasattr(request.app.state, 'data_source_gateway'):
            return {
                "success": False,
                "healthy": False,
                "message": "DataSourceGateway not initialized"
            }
        
        gateway = request.app.state.data_source_gateway
        
        # 获取所有 chain 的健康状态
        health_status = {
            "healthy": True,
            "chains": {}
        }
        
        for data_type, chain in gateway._chains.items():
            stats = chain.get_stats()
            chain_healthy = stats.overall_success_rate > 0.5 if stats.total_requests > 0 else True
            
            health_status["chains"][str(data_type)] = {
                "healthy": chain_healthy,
                "total_requests": stats.total_requests,
                "success_rate": stats.overall_success_rate,
                "providers": len(chain.providers)
            }
            
            if not chain_healthy:
                health_status["healthy"] = False
        
        return {
            "success": True,
            **health_status
        }
    except Exception as e:
        logger.error(f"Error getting gateway health: {e}", exc_info=True)
        return {
            "success": False,
            "healthy": False,
            "error": str(e)
        }


@router.post("/circuit-breaker/{service_name}/reset")
async def reset_circuit_breaker(service_name: str, request: Request):
    """重置指定服务的熔断器
    
    Args:
        service_name: 服务名称 (e.g., "mootdx-source")
    """
    try:
        if not hasattr(request.app.state, 'data_source_gateway'):
            raise HTTPException(
                status_code=503,
                detail="DataSourceGateway not initialized"
            )
        
        gateway = request.app.state.data_source_gateway
        
        # 查找包含该服务的chain并重置熔断器
        reset_count = 0
        for data_type, chain in gateway._chains.items():
            if service_name in chain._circuit_breakers:
                cb = chain._circuit_breakers[service_name]
                cb.reset()
                reset_count += 1
                logger.info(f"Reset circuit breaker for {service_name} in {data_type}")
        
        if reset_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Service {service_name} not found in any chain"
            )
        
        return {
            "success": True,
            "message": f"Reset {reset_count} circuit breaker(s) for {service_name}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting circuit breaker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
