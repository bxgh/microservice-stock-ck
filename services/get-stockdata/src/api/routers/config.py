"""
Stock Pool Configuration Management API

Provides RESTful endpoints for managing stock pool configuration:
- GET /config/current - Get current configuration
- GET /config/version - Get config version info
- GET /config/summary - Get config summary
- POST /config/reload - Manually trigger config reload
- POST /config/validate - Validate configuration
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/config", tags=["Configuration Management"])
internal_router = APIRouter(prefix="/internal/config", tags=["Internal Config API"])

# 全局ConfigManager实例（将由main.py设置）
_config_manager = None


def set_config_manager(manager):
    """设置全局ConfigManager实例"""
    global _config_manager
    _config_manager = manager
    logger.info("✅ ConfigManager set for API routes")


def get_config_manager():
    """获取ConfigManager实例"""
    if _config_manager is None:
        raise HTTPException(
            status_code=500,
            detail="ConfigManager not initialized"
        )
    return _config_manager


@router.get("/current")
async def get_current_config():
    """
    获取当前完整配置
    
    Returns:
        dict: 完整配置字典
    """
    try:
        manager = get_config_manager()
        return {
            "success": True,
            "data": manager.config
        }
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/version")
async def get_config_version():
    """
    获取配置版本信息
    
    Returns:
        dict: 版本信息
    """
    try:
        manager = get_config_manager()
        return {
            "success": True,
            "data": {
                "version": manager.config_version,
                "updated_at": (
                    manager.config_updated_at.isoformat() 
                    if manager.config_updated_at 
                    else None
                ),
                "path": str(manager.config_path)
            }
        }
    except Exception as e:
        logger.error(f"获取版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_config_summary():
    """
    获取配置摘要信息
    
    Returns:
        dict: 配置摘要
    """
    try:
        manager = get_config_manager()
        return {
            "success": True,
            "data": manager.get_config_summary()
        }
    except Exception as e:
        logger.error(f"获取摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_config():
    """
    手动触发配置重载
    
    Returns:
        dict: 重载结果
    """
    try:
        manager = get_config_manager()
        await manager.reload_config()
        return {
            "success": True,
            "message": "配置已重新加载",
            "data": {
                "version": manager.config_version,
                "updated_at": (
                    manager.config_updated_at.isoformat() 
                    if manager.config_updated_at 
                    else None
                )
            }
        }
    except Exception as e:
        logger.error(f"配置重载失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_config():
    """
    验证当前配置是否有效（不修改实际配置）
    
    Returns:
        dict: 验证结果
    """
    try:
        manager = get_config_manager()
        
        # 尝试验证配置
        manager._validate_config(manager.config)
        
        return {
            "success": True,
            "message": "配置验证通过",
            "data": {
                "version": manager.config_version,
                "valid": True
            }
        }
    except ValueError as e:
        return {
            "success": False,
            "message": "配置验证失败",
            "data": {
                "valid": False,
                "error": str(e)
            }
        }
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active_mode")
async def get_active_mode():
    """
    获取当前激活的股票池模式
    
    Returns:
        dict: 激活模式信息
    """
    try:
        manager = get_config_manager()
        active_mode = manager.config.get('active_mode', 'unknown')
        mode_config = manager.get_active_pool_config()
        
        return {
            "success": True,
            "data": {
                "active_mode": active_mode,
                "config": mode_config
            }
        }
    except Exception as e:
        logger.error(f"获取激活模式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blacklist/check")
async def check_blacklist(
    code: str = Query(..., description="股票代码"),
    name: str = Query(None, description="股票名称（可选）")
):
    """
    检查股票是否在黑名单中
    
    Args:
        code: 股票代码
        name: 股票名称（可选）
        
    Returns:
        dict: 检查结果
    """
    try:
        manager = get_config_manager()
        stock_info = {"名称": name} if name else None
        is_blacklisted = manager.is_blacklisted(code, stock_info)
        
        return {
            "success": True,
            "data": {
                "code": code,
                "name": name,
                "is_blacklisted": is_blacklisted
            }
        }
    except Exception as e:
        logger.error(f"黑名单检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Internal APIs ====================

@internal_router.get("/health")
async def config_health():
    """
    配置管理器健康检查（内部接口）
    
    Returns:
        dict: 健康状态
    """
    try:
        manager = get_config_manager()
        return {
            "status": "healthy",
            "version": manager.config_version,
            "watching": manager._watching,
            "callbacks_registered": len(manager.reload_callbacks)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
