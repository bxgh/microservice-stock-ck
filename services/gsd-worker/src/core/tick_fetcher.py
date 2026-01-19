
import asyncio
import logging
import aiohttp
import pytz
from datetime import datetime
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class TickFetcher:
    """
    分笔数据采集器
    核心策略: Smart Matrix Search
    """
    
    # 搜索矩阵: (start, offset, description)
    SEARCH_MATRIX = [
        (0, 5000, "全量基础"),
        (3500, 800, "万科A前区域"),
        (4000, 500, "万科A原成功"),
        (4500, 800, "万科A后区域"),
        (3000, 1000, "深度区域1"),
        (5000, 1000, "深度区域2"),
        (6000, 1200, "深度区域3"),
        (2000, 1500, "广域区域1"),
        (7000, 1500, "广域区域2"),
    ]
    
    TARGET_TIME = "09:25"

    def __init__(self, http_session: aiohttp.ClientSession, api_url: str):
        self.http = http_session
        self.api_url = api_url

    async def fetch(self, stock_code: str, trade_date: str) -> List[Dict[str, Any]]:
        """执行智能矩阵搜索采集数据"""
        start_time = asyncio.get_running_loop().time()
        all_frames = []
        
        # Strip leading dot from stock code (K-line table format: .600001, API needs: 600001)
        clean_code = stock_code.lstrip('.')
        
        today_str = datetime.now(CST).strftime("%Y%m%d")
        is_today = (trade_date == today_str)
        
        if is_today:
            # 当日数据保持原有矩阵搜索 (速度优先，通常全天分笔不多)
            for i, (start, offset, description) in enumerate(self.SEARCH_MATRIX):
                try:
                    url = f"{self.api_url}/api/v1/tick/{clean_code}"
                    params = {"start": start, "offset": offset}
                    
                    logger.info(f"🔍 {stock_code}: GET {url} params={params}")
                    async with self.http.get(url, params=params, timeout=12) as response:
                        if response.status != 200: continue
                        data = await response.json()
                        if not data: continue
                        
                        all_frames.append(data)
                        times = [x.get('time', '') for x in data]
                        if times and min(times) <= self.TARGET_TIME:
                            logger.debug(f"🎯 {stock_code}: 命中 {self.TARGET_TIME} @ {description}")
                            break
                except Exception as e:
                    logger.warning(f"{stock_code} 步骤 {description} 异常: {e}")
        else:
            # 历史数据改用线性扫描，步进 2000 (解决 API 2000条上限问题)
            max_depth = 50000 
            step = 2000
            current_start = 0
            
            logger.info(f"🚀 {stock_code}: 开始历史分笔线性扫描 (目标日期: {trade_date})")
            while current_start < max_depth:
                try:
                    url = f"{self.api_url}/api/v1/tick/{clean_code}"
                    params = {"date": int(trade_date), "start": current_start, "offset": step}
                    
                    async with self.http.get(url, params=params, timeout=15) as response:
                        if response.status != 200:
                            logger.warning(f"⚠️ {stock_code}: 接口返回异常 {response.status} @ start={current_start}")
                            break
                        
                        data = await response.json()
                        if not data:
                            logger.debug(f"⏹️ {stock_code}: 无更多数据 @ start={current_start}")
                            break
                        
                        all_frames.append(data)
                        times = [x.get('time', '') for x in data]
                        earliest = min(times) if times else "23:59"
                        
                        logger.info(f"📥 {stock_code}: 获取 {len(data)} 条 (earliest: {earliest}) @ start={current_start}")
                        
                        # 早停: 命中 09:25
                        if earliest <= self.TARGET_TIME:
                            logger.info(f"🎯 {stock_code}: 线性扫描完成 (已覆盖 {self.TARGET_TIME})")
                            break
                        
                        current_start += step
                except Exception as e:
                    logger.error(f"❌ {stock_code} 采集异常 (start={current_start}): {e}")
                    break
        
        return self._merge_and_sort(all_frames)

    def _merge_and_sort(self, frames: List[List[Dict]]) -> List[Dict]:
        """合并、去重、排序"""
        if not frames:
            return []
            
        merged = []
        for frame in frames:
            merged.extend(frame)
            
        # 严格去重 (time, price, volume)
        seen = set()
        final_data = []
        for item in merged:
            key = (
                item.get('time'), 
                item.get('price'), 
                item.get('vol', item.get('volume'))
            )
            if key not in seen:
                seen.add(key)
                final_data.append(item)
        
        # 排序
        final_data.sort(key=lambda x: x.get('time', ''))
        return final_data
