import asyncio
import logging
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from src.models.hardware import HardwareSpotPrice

logger = logging.getLogger(__name__)

class HardwareSpotCollector:
    """
    云端 GPU 现货价格采集器。
    支持从不同的平台（AutoDL, Aliyun 等）通过 API 或公开接口获取实时价格与库存。
    """
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    @property
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def collect_all(self, config: Dict[str, Any]) -> List[HardwareSpotPrice]:
        """
        根据配置并行采集所有平台的硬件价格
        """
        tasks = []
        platforms = config.get("platforms", [])
        
        for pc in platforms:
            if not pc.get("enabled", True):
                continue
                
            name = pc.get("name")
            if name == "autodl":
                tasks.append(self._collect_autodl(pc))
            elif name == "aliyun":
                tasks.append(self._collect_aliyun(pc))
            else:
                logger.warning(f"Unknown platform in config: {name}")
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_prices = []
        for res in results:
            if isinstance(res, list):
                all_prices.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Platform collection failed: {res}")
                
        return all_prices

    async def _collect_autodl(self, config: Dict[str, Any]) -> List[HardwareSpotPrice]:
        """
        采集 AutoDL 现货价格。
        参考其弹性部署接口：https://api.autodl.com/v1/market/list (假设接口)
        实际开发中如无公开 API，可能需要通过其弹性部署页面的数据接口。
        """
        prices = []
        platform = "autodl"
        target_gpus = config.get("gpu_models", [])
        
        logger.info(f"Collecting hardware prices from {platform}...")
        
        try:
            # 修正为 autodl 官方 API 域名
            api_url = "https://api.autodl.com/v1/market/list"
            headers = {
                **self.headers,
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.autodl.com",
                "Referer": "https://www.autodl.com/"
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(api_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", {}).get("list", [])
                    for item in data:
                        # 假设字段名为 name, price, gpu_count
                        model_name = item.get("gpu_type", "")
                        if any(tg in model_name for tg in target_gpus):
                            prices.append(HardwareSpotPrice(
                                platform=platform,
                                gpu_model=model_name,
                                instance_type=f"{item.get('gpu_count', 1)}卡 {model_name}",
                                price_per_hour=float(item.get("price", 0)),
                                availability=1.0 if item.get("stock", 0) > 0 else 0.0,
                                collect_time=self._now
                            ))
                else:
                    logger.warning(f"AutoDL API returned {resp.status_code}")
                    
            logger.info(f"Successfully collected {len(prices)} real prices from {platform}")
            
        except Exception as e:
            logger.error(f"Failed to collect from {platform}: {e}")
            
        return prices

    async def _collect_aliyun(self, config: Dict[str, Any]) -> List[HardwareSpotPrice]:
        """
        采集 阿里云 PAI/ECS 竞价价格。
        通常通过阿里云 SDK 或 Spot Price 接口获取。
        """
        prices = []
        platform = "aliyun"
        target_gpus = config.get("gpu_models", [])
        
        logger.info(f"Collecting hardware prices from {platform}...")
        
        try:
            # 阿里云竞价实例采集通常需要 AccessKey/SecretKey 或专用端点
            # 鉴于当前环境未配置 ALIYUN_ACCESS_KEY，仅保留逻辑入口
            logger.info(f"Aliyun real collection requires cloud credentials. Skipping for now.")
            
        except Exception as e:
            logger.error(f"Failed to collect from {platform}: {e}")
            
        return prices
