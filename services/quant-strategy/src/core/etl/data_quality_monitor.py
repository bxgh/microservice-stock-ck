
"""
数据质量监控模块 (DataQualityMonitor)
对应 Story 002.05
负责从 Redis 读取 Gate-3 审计结果，并执行因子级拓扑校验
"""
import logging

import pandas as pd
from gsd_shared.validation import QualityLevel, SnapshotValidator

from adapters.clickhouse_loader import ClickHouseLoader
from cache.redis_client import redis_client

logger = logging.getLogger(__name__)


class DataQualityMonitor:
    def __init__(self, loader: ClickHouseLoader | None = None):
        self.loader = loader if loader else ClickHouseLoader()
        # Redis Key Patterns (Aligned with gsd-shared)
        self.SYNC_STATUS_KEY = "tick_sync:status:{date}"

    async def get_sync_status(self, stock_code: str, trade_date: str) -> dict[str, str]:
        """
        从 Redis 读取同步状态
        格式: status|count|start|end|sync_time|error
        """
        key = self.SYNC_STATUS_KEY.format(date=trade_date)
        try:
            if not redis_client._client:
                await redis_client.initialize()

            # Using hget directly
            raw_val = await redis_client._client.hget(key, stock_code)
            if not raw_val:
                return {"status": "MISSING", "reason": "No sync status in Redis"}

            parts = raw_val.split('|')
            status = parts[0] if len(parts) > 0 else "UNKNOWN"
            error = parts[5] if len(parts) > 5 else ""

            return {
                "status": status,
                "error": error,
                "raw": raw_val
            }
        except Exception as e:
            logger.error(f"Failed to fetch sync status for {stock_code} on {trade_date}: {e}")
            return {"status": "ERROR", "reason": str(e)}

    def verify_tick_topology(self, ticks_df: pd.DataFrame) -> tuple[str, str]:
        """
        因子级拓扑校验: 检测乱序和时间戳冲突
        """
        if ticks_df.empty:
            return QualityLevel.FAIL, "Empty ticks"

        df = ticks_df.copy()

        # 1. 检查时间戳是否有序
        # Assuming tick_time is already processed or raw
        # If raw string, convert to numeric proxy or just compare
        # ClickHouse order is usually sorted, but we check again.
        is_sorted = df['tick_time'].is_monotonic_increasing
        if not is_sorted:
            # Check deviation
            (df['tick_time'].diff() < pd.Timedelta(0)).sum() if pd.api.types.is_timedelta64_dtype(df['tick_time']) else 0
            # If we can't easily diff, just mark as WARN if not monotonic
            return QualityLevel.WARN, "Ticks are not monotonic"

        # 2. 检查价格跳空 (针对特征 A/B 敏感度)
        df['price_pct'] = df['price'].astype(float).pct_change().abs()
        heavy_jumps = (df['price_pct'] > 0.05).sum() # 单笔跳空 > 5%
        if heavy_jumps > 0:
            return QualityLevel.WARN, f"Detected {heavy_jumps} abnormal price jumps (>5%)"

        return QualityLevel.PASS, "OK"

    async def verify_snapshot_quality(self, snapshot_df: pd.DataFrame, stock_code: str, trade_date: str) -> tuple[str, str]:
        """
        全量快照质量校验 (Story 2.05 增强项) - 已下沉至 gsd-shared
        """
        if snapshot_df.empty:
            return QualityLevel.FAIL, "No snapshots"

        # 1. 密度与单调性校验 (直接调用公共库)
        is_ok, msg = await SnapshotValidator.validate_all(snapshot_df)
        if not is_ok:
            return QualityLevel.FAIL, msg

        # 2. K线对账 (个股增强：获取实际 K 线数据)
        try:
            if self.loader.client is None:
                await self.loader.initialize()

            kline_query = """
                SELECT high_price as high, low_price as low, volume, amount FROM stock_kline_daily
                WHERE stock_code LIKE %(code)s || '%%' AND toDate(trade_date) = %(date)s
            """
            kline_res = self.loader.client.execute(kline_query, {'code': stock_code, 'date': trade_date})

            if kline_res:
                k_data = {
                    'high': kline_res[0][0],
                    'low': kline_res[0][1],
                    'volume': kline_res[0][2],
                    'amount': kline_res[0][3]
                }
                level, msg = SnapshotValidator.verify_with_kline(snapshot_df, k_data)
                return level, msg

        except Exception as e:
            logger.error(f"K-line benchmark failed for {stock_code}: {e}")

        return QualityLevel.PASS, "OK"

    def check_ohlc_consistency(self, cleaned_df: pd.DataFrame, snapshot_df: pd.DataFrame) -> tuple[str, str]:
        """
        检查生成的分钟序列与原始快照的一致性
        """
        if cleaned_df.empty or snapshot_df.empty:
            return QualityLevel.FAIL, "Input data empty"

        # 简单比对最后一笔价格和累计成交量
        cleaned_last_price = cleaned_df['close'].iloc[-1]
        snap_last_price = snapshot_df['current_price'].iloc[-1]

        price_diff = abs(float(cleaned_last_price) - float(snap_last_price))
        if price_diff > 0.05: # 容忍度
            return QualityLevel.WARN, f"Price mismatch: Cleaned({cleaned_last_price}) vs Snap({snap_last_price})"

        return QualityLevel.PASS, "OK"

    async def check_if_active(self, stock_code: str, trade_date: str) -> bool:
        """
        通过 stock_kline_daily 检查股票当天是否活跃 (非停牌/退市)
        """
        try:
            if self.loader.client is None:
                await self.loader.initialize()

            query = """
                SELECT count() FROM stock_kline_daily
                WHERE stock_code LIKE %(code)s || '%%' AND toDate(trade_date) = %(date)s
            """
            result = self.loader.client.execute(query, {'code': stock_code, 'date': trade_date})
            return result[0][0] > 0
        except Exception as e:
            logger.error(f"Failed to check active status for {stock_code}: {e}")
            return True # Fallback to true if query fails

    def check_amount_deviation(self, ticks_df: pd.DataFrame) -> tuple[str, str]:
        """
        金额偏离度校验: abs(Amount / (Price * Vol) - 1) < 0.02
        """
        if ticks_df.empty:
            return QualityLevel.PASS, "OK"

        # Calculate deviation for non-zero volume/price
        mask = (ticks_df['volume'] > 0) & (ticks_df['price'] > 0)
        valid_ticks = ticks_df[mask].copy()

        if valid_ticks.empty:
            return QualityLevel.PASS, "OK"

        valid_ticks['calc_amt'] = valid_ticks['price'] * valid_ticks['volume']
        valid_ticks['deviation'] = (valid_ticks['amount'] / valid_ticks['calc_amt'] - 1).abs()

        median_dev = valid_ticks['deviation'].median()
        if median_dev > 0.05: # Using 5% for median as a fail threshold
             return QualityLevel.FAIL, f"Extreme amount deviation (median: {median_dev:.2%})"
        elif median_dev > 0.02:
             return QualityLevel.WARN, f"Significant amount deviation (median: {median_dev:.2%})"

        return QualityLevel.PASS, "OK"

    async def is_qualified(self, stock_code: str, trade_date: str,
                         ticks_df: pd.DataFrame | None = None,
                         cleaned_df: pd.DataFrame | None = None,
                         snapshot_df: pd.DataFrame | None = None) -> tuple[bool, str]:
        """
        综合判定是否合格
        """
        # 1. 活跃度检查 (Benchmark: stock_kline_daily)
        is_active = await self.check_if_active(stock_code, trade_date)
        if not is_active:
             return False, "Stock not active in stock_kline_daily (Suspended or Retired)"

        # 2. Check Sync Status (Gate-3 inherited)
        sync_info = await self.get_sync_status(stock_code, trade_date)
        if sync_info['status'] != "SUCCESS":
            return False, f"Gate-3 Status: {sync_info['status']} ({sync_info.get('error', '')})"

        # 3. 因子级检查
        if ticks_df is not None:
            # 3.1 拓扑校验
            t_level, t_msg = self.verify_tick_topology(ticks_df)
            if t_level == QualityLevel.FAIL:
                return False, f"Topology: {t_msg}"

            # 3.2 金额校验
            a_level, a_msg = self.check_amount_deviation(ticks_df)
            if a_level == QualityLevel.FAIL:
                return False, f"Amount: {a_msg}"

        # 4. Snapshot Quality Check (Story 2.05 增强)
        if snapshot_df is not None:
            s_level, s_msg = await self.verify_snapshot_quality(snapshot_df, stock_code, trade_date)
            if s_level == QualityLevel.FAIL:
                return False, f"Snapshot Quality: {s_msg}"

        # 5. Consistency Check (OHLC)
        if cleaned_df is not None and snapshot_df is not None:
            c_level, c_msg = self.check_ohlc_consistency(cleaned_df, snapshot_df)
            if c_level == QualityLevel.FAIL:
                return False, f"Consistency: {c_msg}"

        return True, "Qualified"
