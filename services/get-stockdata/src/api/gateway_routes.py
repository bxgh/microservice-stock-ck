# -*- coding: utf-8 -*-
"""
Gateway 监控路由

提供 DataSourceGateway 的监控和统计接口
"""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel
import logging
import json

# gRPC Proto (EPIC-006)
try:
    from datasource.v1 import data_source_pb2
    GRPC_AVAILABLE = True
except ImportError:
    data_source_pb2 = None
    GRPC_AVAILABLE = False

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

# ========== 数据获取端点 (通过 gRPC 调用 mootdx-source) ==========

class QuotesRequest(BaseModel):
    codes: List[str]

class HistoryRequest(BaseModel):
    code: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    frequency: str = "d"
    adjust: str = "2"


@router.post("/data/quotes")
async def fetch_quotes_via_grpc(req: QuotesRequest, request: Request):
    """通过 gRPC Gateway 获取实时行情
    
    调用 mootdx-source:50051 获取行情数据
    
    Args:
        codes: 股票代码列表 (如 ["600519", "000001"])
    
    Returns:
        实时行情数据
    """
    try:
        if not hasattr(request.app.state, 'data_source_gateway'):
            raise HTTPException(status_code=503, detail="DataSourceGateway not initialized")
        
        if not GRPC_AVAILABLE:
            raise HTTPException(status_code=503, detail="gRPC proto not available")
        
        gateway = request.app.state.data_source_gateway
        
        # 构建 gRPC 请求
        grpc_request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_QUOTES,
            codes=req.codes
        )
        
        response = await gateway.fetch(grpc_request)
        
        if not response.success:
            return {
                "success": False,
                "error": response.error_message,
                "source": response.source_name
            }
        
        # 解析 JSON 数据
        data = json.loads(response.json_data) if response.json_data else []
        
        return {
            "success": True,
            "source": response.source_name,
            "latency_ms": response.latency_ms,
            "count": len(data),
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quotes via gRPC: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/history")
async def fetch_history_via_grpc(req: HistoryRequest, request: Request):
    """通过 gRPC Gateway 获取历史K线
    
    调用 mootdx-source → baostock-api 获取历史数据
    
    Args:
        code: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        frequency: 周期 (d/w/m)
        adjust: 复权类型 (1=后复权, 2=前复权, 3=不复权)
    """
    try:
        if not hasattr(request.app.state, 'data_source_gateway'):
            raise HTTPException(status_code=503, detail="DataSourceGateway not initialized")
        
        if not GRPC_AVAILABLE:
            raise HTTPException(status_code=503, detail="gRPC proto not available")
        
        gateway = request.app.state.data_source_gateway
        
        params = {}
        if req.start_date:
            params["start_date"] = req.start_date
        if req.end_date:
            params["end_date"] = req.end_date
        params["frequency"] = req.frequency
        params["adjust"] = req.adjust
        
        grpc_request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_HISTORY,
            codes=[req.code],
            params=params
        )
        
        response = await gateway.fetch(grpc_request)
        
        if not response.success:
            return {
                "success": False,
                "error": response.error_message,
                "source": response.source_name
            }
        
        data = json.loads(response.json_data) if response.json_data else []
        
        return {
            "success": True,
            "source": response.source_name,
            "latency_ms": response.latency_ms,
            "count": len(data),
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history via gRPC: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/ranking/{ranking_type}")
async def fetch_ranking_via_grpc(ranking_type: str, request: Request):
    """通过 gRPC Gateway 获取榜单数据
    
    调用 mootdx-source → akshare-api 获取榜单
    
    Args:
        ranking_type: 榜单类型 (hot/surge/limit_up/dragon_tiger)
    """
    try:
        if not hasattr(request.app.state, 'data_source_gateway'):
            raise HTTPException(status_code=503, detail="DataSourceGateway not initialized")
        
        if not GRPC_AVAILABLE:
            raise HTTPException(status_code=503, detail="gRPC proto not available")
        
        gateway = request.app.state.data_source_gateway
        
        grpc_request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_RANKING,
            params={"ranking_type": ranking_type}
        )
        
        response = await gateway.fetch(grpc_request)
        
        if not response.success:
            return {
                "success": False,
                "error": response.error_message,
                "source": response.source_name
            }
        
        data = json.loads(response.json_data) if response.json_data else []
        
        return {
            "success": True,
            "source": response.source_name,
            "latency_ms": response.latency_ms,
            "ranking_type": ranking_type,
            "count": len(data),
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ranking via gRPC: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/{code}")
async def test_grpc_gateway(code: str, request: Request):
    """快速测试 gRPC Gateway 连通性
    
    获取单只股票的行情数据验证端到端链路
    """
    try:
        if not hasattr(request.app.state, 'data_source_gateway'):
            return {
                "success": False,
                "error": "DataSourceGateway not initialized",
                "grpc_mode": False
            }
        
        if not GRPC_AVAILABLE:
            return {
                "success": False,
                "error": "gRPC proto not available",
                "grpc_mode": False
            }
        
        gateway = request.app.state.data_source_gateway
        
        grpc_request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_QUOTES,
            codes=[code]
        )
        
        response = await gateway.fetch(grpc_request)
        
        return {
            "success": response.success,
            "grpc_mode": True,
            "source": response.source_name,
            "latency_ms": response.latency_ms,
            "error": response.error_message if not response.success else None,
            "data_preview": response.json_data[:200] if response.json_data else None
        }
    except Exception as e:
        logger.error(f"Error testing gRPC gateway: {e}", exc_info=True)
        return {
            "success": False,
            "grpc_mode": False,
            "error": str(e)
        }

