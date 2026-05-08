"""
异动评分权重 DAO
"""
import logging
import pandas as pd
from typing import List, Optional, Dict, Any
import aiomysql

logger = logging.getLogger(__name__)

class AnomalyDAO:
    """异动评分权重访问对象"""

    async def get_weights_by_version(self, pool: aiomysql.Pool, version: str = 'v1') -> Dict[str, float]:
        """
        根据版本号获取异动评分权重配置
        
        Args:
            pool: aiomysql 连接池
            version: 权重版本号 (如 'v1')
            
        Returns:
            Dict[str, float]: 权重字典 {weight_key: weight_value}
        """
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT weight_key, weight_value 
                        FROM dim_anomaly_score_weight 
                        WHERE version = %s AND is_active = 1 AND is_deleted = 0
                    """
                    await cursor.execute(query, (version,))
                    rows = await cursor.fetchall()
                    
                    if not rows:
                        logger.warning(f"未找到版本为 {version} 的激活权重配置")
                        return {}
                    
                    # 转换为字典格式并确保数值为 float (MySQL DECIMAL 会转为 Decimal 对象)
                    weights = {row['weight_key']: float(row['weight_value']) for row in rows}
                    return weights
                    
        except Exception as e:
            logger.error(f"获取异动权重 (version={version}) 失败: {e}")
            return {}

    async def get_all_weight_versions(self, pool: aiomysql.Pool) -> List[str]:
        """获取所有可用的权重版本"""
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    query = "SELECT DISTINCT version FROM dim_anomaly_score_weight WHERE is_deleted = 0"
                    await cursor.execute(query)
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"获取权重版本列表失败: {e}")
            return []
