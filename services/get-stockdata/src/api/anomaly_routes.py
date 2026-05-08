# -*- coding: utf-8 -*-
"""
异动捕捉与评分配置 API Routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
import logging
from typing import Dict, Any

from data_access.mysql_pool import MySQLPoolManager
from data_access.anomaly_dao import AnomalyDAO

router = APIRouter(prefix="/api/v1/anomaly", tags=["异动捕捉系统"])
logger = logging.getLogger(__name__)

async def get_mysql_pool():
    return await MySQLPoolManager.get_pool()

@router.get("/weights")
async def get_anomaly_weights(
    version: str = Query("v1", description="权重版本号 (如 v1, v2)"),
    pool = Depends(get_mysql_pool)
):
    """
    获取指定版本的异动评分权重配置 - 直连 MySQL
    """
    try:
        weights = await AnomalyDAO().get_weights_by_version(pool, version)
        if not weights:
            raise HTTPException(status_code=404, detail=f"No weights found for version {version}")
            
        return {
            "success": True,
            "data": {
                "version": version,
                "weights": weights
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching anomaly weights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching anomaly weights: {str(e)}")

@router.get("/weights/versions")
async def list_weight_versions(pool = Depends(get_mysql_pool)):
    """
    列出所有可用的权重版本
    """
    try:
        versions = await AnomalyDAO().get_all_weight_versions(pool)
        return {
            "success": True,
            "data": versions
        }
    except Exception as e:
        logger.error(f"Error listing weight versions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing weight versions: {str(e)}")
