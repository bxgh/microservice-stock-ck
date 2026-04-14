"""
流动性指标分析器
"""
import logging
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class LiquidityMomentumAnalyzer:
    """
    VOL-01: 成交额均线背离 (Liquidity Moving Average Divergence)
    通过双指数聚合测度宏观流动性动能。
    """
    
    def __init__(self, mootdx_api_url: str = "http://127.0.0.1:8003"):
        self.api_url = mootdx_api_url.rstrip('/')
        self.start_date = "2024-01-01"

    async def analyze_vol01(self, sh_df: pd.DataFrame, sz_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """执行 VOL-01 分析 (接收预加载的指数数据)"""
        logger.info("Starting VOL-01 analysis (Preloaded Indices)...")
        
        if sh_df.empty or sz_df.empty:
            logger.error("Required index data is empty.")
            return None

        # 2. 对齐与合并
        df = pd.merge(sh_df, sz_df, on='datetime', suffixes=('_sh', '_sz'))
        df['Volume_Total'] = df['amount_sh'] + df['amount_sz']
        
        # 3. 时间清洗（锚定 2024-01-01）
        df = df[df['datetime'] >= self.start_date].copy()
        df = df.sort_values('datetime').reset_index(drop=True)
        
        if len(df) < 20:
            logger.warning("Insufficient history for MA20 calculation.")
            return None

        # 4. 计算移动平均线与偏离度
        df['MA5'] = df['Volume_Total'].rolling(window=5).mean()
        df['MA20'] = df['Volume_Total'].rolling(window=20).mean()
        df['delta_vol'] = (df['MA5'] - df['MA20']) / df['MA20']
        
        # 5. 三层分值体系 (Expanding Rank)
        # Rank_vol: 日线分值
        df['Rank_vol'] = df['Volume_Total'].expanding().apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])
        # Rank_MA5: 周线分值
        df['Rank_MA5'] = df['MA5'].expanding().apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])
        # Rank_MA20: 月线分值
        df['Rank_MA20'] = df['MA20'].expanding().apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])

        # 6. 状态机逻辑内联
        df['delta_vol_diff'] = df['delta_vol'].diff()
        
        # 7. 日历效应噪音过滤 (P2 修复)
        # 识别长假导致的交易日断层 (gap >= 6天)
        df['gap_days'] = df['datetime'].diff().dt.days
        df['is_post_holiday'] = df['gap_days'] >= 6
        
        # 识别节前末周 (未来5个交易日内会出现长假断层)
        df['is_pre_holiday'] = df['gap_days'].shift(-1).iloc[::-1].rolling(window=5, min_periods=1).max().iloc[::-1] >= 6
        
        # 计算经过清洗的环比变化率用于基准统计
        df['pct_chg'] = df['Volume_Total'].pct_change()
        df['clean_pct_chg'] = np.where(df['is_post_holiday'] | df['is_pre_holiday'], np.nan, df['pct_chg'])
        df['mu'] = df['clean_pct_chg'].expanding().mean()
        df['sigma'] = df['clean_pct_chg'].expanding().std()
        
        return df

    def analyze_vol02(self, df_vol: pd.DataFrame, df_margin: pd.DataFrame) -> pd.DataFrame:
        """
        [VOL-02] 融资买入动量的加速度计算
        $R_{margin} = Margin Buy / Volume Total$
        """
        # 1. 预处理
        df_vol['date'] = df_vol['datetime'].dt.date
        df_margin['date'] = pd.to_datetime(df_margin['trade_date']).dt.date
        
        # 2. 合并
        df = pd.merge(df_vol, df_margin, on='date', how='inner')
        
        # 3. 计算 $R_{margin}$
        df['margin_ratio'] = df['margin_buy'] / df['Volume_Total']
        
        # 4. 计算动量 (Expanding Window)
        df['margin_ratio_mu'] = df['margin_ratio'].expanding(60).mean()
        df['margin_ratio_sigma'] = df['margin_ratio'].expanding(60).std()
        
        # 5. 计算加速度 (Z-score 衍生)
        df['margin_velocity'] = (df['margin_ratio'] - df['margin_ratio_mu']) / df['margin_ratio_sigma']
        
        return df

    def identify_states(self, df_01: pd.DataFrame, df_02: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        综合判定 VOL-01 和 VOL-02 的状态
        """
        last_01 = df_01.iloc[-1]
        
        # --- VOL-01 状态判定 ---
        is_accel_in = (last_01['Rank_vol'] > 0.9 and 
                       last_01['Rank_MA5'] > 0.9 and 
                       last_01['delta_vol'] > 0)
        
        is_peak = (last_01['Rank_vol'] > 0.95 and 
                   last_01['delta_vol_diff'] < 0)
                          
        is_collapse = False
        if not (last_01.get('is_post_holiday', False) or last_01.get('is_pre_holiday', False)):
            if not pd.isna(last_01.get('mu')) and not pd.isna(last_01.get('sigma')):
                is_collapse = last_01['pct_chg'] < (last_01['mu'] - 2 * last_01['sigma'])
        
        state_01 = "NORMAL"
        if is_collapse: state_01 = "COLLAPSE_RISK"
        elif is_peak: state_01 = "MOMENTUM_PEAK"
        elif is_accel_in: state_01 = "ACCEL_IN"

        # --- VOL-02 状态判定 ---
        state_02 = "NORMAL"
        margin_velocity = 0.0
        margin_ratio = 0.0
        
        if df_02 is not None and not df_02.empty:
            last_02 = df_02.iloc[-1]
            margin_velocity = float(last_02['margin_velocity']) if not pd.isna(last_02['margin_velocity']) else 0.0
            margin_ratio = float(last_02['margin_ratio'])
            
            # PULSED (踊跃): 加速度 > 1 sigma
            # PEAK (极值): 加速度 > 2 sigma
            # DIVERGENCE (背离): 指数缩量但融资买入占比异常上升（通常指主力撤退，散户加杠杆）
            # 或者本规格定义：指数放量但 $R_{margin}$ 下降
            
            if margin_velocity > 2:
                state_02 = "LEVERAGE_PEAK"
            elif margin_velocity > 1:
                state_02 = "PULSED"
            
            # 背离判定：VOL-01 涌入但 VOL-02 占比下降
            if is_accel_in and last_02['margin_ratio'] < last_02['margin_ratio_mu']:
                state_02 = "DIVERGENCE"

        return {
            "trade_date": last_01['datetime'].strftime('%Y-%m-%d'),
            "state_name": state_01,  # 主状态沿用成交量
            "vol_01_state": state_01,
            "vol_02_state": state_02,
            "vol_ma_divergence": float(last_01['delta_vol']),
            "vol_rank": float(last_01['Rank_vol']),
            "vol_ma5_rank": float(last_01['Rank_MA5']),
            "vol_ma20_rank": float(last_01['Rank_MA20']),
            "margin_ratio": margin_ratio,
            "margin_velocity": margin_velocity,
            "is_accel_in": bool(is_accel_in),
            "is_peak": bool(is_peak),
            "is_collapse": bool(is_collapse),
            "volume_total": float(last_01['Volume_Total'])
        }

    def analyze_vol03(self, df_klines: pd.DataFrame, df_industry: pd.DataFrame) -> Dict[str, Any]:
        """
        [VOL-03] 极值拥挤度的加速度 (Siphon Ratio of Top 10% Stocks)
        输入: df_klines (code, amount), df_industry (code, l1_name)
        """
        if df_klines.empty:
            return {"ratio_c": 0.0, "industry_count": 0}
            
        # 1. 计算总成交额
        total_amount = df_klines['amount'].sum()
        if total_amount == 0:
            return {"ratio_c": 0.0, "industry_count": 0}
            
        # 2. 按成交额降序排序，取前 10%
        df_sorted = df_klines.sort_values('amount', ascending=False)
        top_n = max(1, int(len(df_sorted) * 0.1))
        df_top = df_sorted.head(top_n)
        
        # 3. 计算 Ratio_C
        top_amount = df_top['amount'].sum()
        ratio_c = top_amount / total_amount
        
        # 4. 统计行业分布 (需要 JOIN 行业表)
        df_top_with_ind = pd.merge(df_top, df_industry, on='code', how='left')
        industry_count = df_top_with_ind['l1_name'].nunique()
        
        return {
            "ratio_c": float(ratio_c),
            "industry_count": int(industry_count),
            "top_n": top_n
        }

    def analyze_vol04(self, df_klines: pd.DataFrame, df_basic: pd.DataFrame) -> Dict[str, Any]:
        """
        [VOL-04] 极寒无流动性股衍生率 (Zombie Stock Derivation)
        输入: df_klines (code, turnover), df_basic (code, circ_mv)
        """
        if df_klines.empty:
            return {"count_frozen": 0, "total_scanned": 0}
            
        # 1. 合并市值数据
        # 注意: 代码字段在 klines 中是 'code', 在 basic 中也统一为 'code' (Job 层处理)
        df = pd.merge(df_klines, df_basic, on='code', how='left')
        
        # 2. 过滤市值 <= 50 亿 (500,000 万元)
        # 采用 A 方案: 缺失值的标的已由 Job 层通过最近有效值填充，若仍缺失则排除
        df_filtered = df[df['circ_mv'] <= 500000].copy()
        
        if df_filtered.empty:
            return {"count_frozen": 0, "total_scanned": len(df)}
            
        # 3. 统计换手率 <= 0.5% 的数量
        # 注意: kline.turnover 通常是百分比 (如 0.5 表示 0.5%)，需检查数据源
        count_frozen = len(df_filtered[df_filtered['turnover'] <= 0.5])
        
        return {
            "count_frozen": int(count_frozen),
            "total_scanned": len(df_filtered)
        }

    def analyze_vol05(self, df_repo: pd.DataFrame) -> Dict[str, Any]:
        """
        [VOL-05] 资金成本的异常脉冲 (FDR007) 及非银行溢价 (R007-FR007)
        输入: df_repo (trade_date, repo_code, close)
        """
        if df_repo.empty:
            return {"pulse_fdr007": 0.0, "spread": 0.0}
            
        # 1. 整理数据为宽表 (先去重处理，防止 Index contains duplicate entries 错误)
        df_repo_clean = df_repo.drop_duplicates(subset=['trade_date', 'repo_code'], keep='last')
        df_pivot = df_repo_clean.pivot(index='trade_date', columns='repo_code', values='close').sort_index()
        
        if 'FR007' not in df_pivot.columns:
            return {"pulse_fdr007": 0.0, "spread": 0.0}
            
        # 2. 计算 Spread (R007 - FR007) BP
        spread = 0.0
        if 'R007' in df_pivot.columns:
            # 这里的 close 通常是百分比 (如 2.5 表示 2.5%)，利差使用 BP (万分之一)
            spread = (df_pivot['R007'] - df_pivot['FR007']) * 100
            
        # 3. 计算 FR007 脉冲 (Z-Score of log(FR007))
        # 规格定义使用 60 日窗口
        log_fdr = np.log(df_pivot['FR007'])
        z_scores = self.compute_zscore(log_fdr, window=60)
        
        last_pulse = float(z_scores.iloc[-1]) if not pd.isna(z_scores.iloc[-1]) else 0.0
        last_spread = float(spread.iloc[-1]) if not pd.isna(spread.iloc[-1]) else 0.0
        
        return {
            "pulse_fdr007": last_pulse,
            "spread": last_spread
        }

    def analyze_vol06(self, df_etf: pd.DataFrame, df_index: pd.DataFrame) -> Dict[str, Any]:
        """
        [VOL-06] ETF 被动护盘效用消耗 (Intervention Depletion)
        输入: 
            df_etf: 510300 ETF 日成交量序列 (datetime, volume)
            df_index: 指数日收益率序列 (datetime, pct_chg)
        计算: Index_Ret = k * Z(ETF_Vol) + b
        """
        if df_etf.empty or df_index.empty:
            return {"depletion_slope": 0.0}
            
        # 1. 计算 ETF 成交量 Z-Score (20日窗口)
        df_etf = df_etf.sort_values('datetime')
        df_etf['vol_z'] = self.compute_zscore(df_etf['volume'], window=20)
        
        # 2. 合并指数收益率
        df_merged = pd.merge(df_etf[['datetime', 'vol_z']], df_index[['datetime', 'pct_chg']], on='datetime')
        df_merged = df_merged.dropna()
        
        if len(df_merged) < 10:  # 样本量不足
            return {"depletion_slope": 0.0}
            
        # 3. 线性回归 (取最近 20 个交易日计算斜率)
        df_reg = df_merged.tail(20)
        x = df_reg['vol_z'].values
        y = df_reg['pct_chg'].values
        
        try:
            # y = kx + b
            k, b = np.polyfit(x, y, 1)
            return {"depletion_slope": float(k)}
        except:
            return {"depletion_slope": 0.0}

    @staticmethod
    def winsorize(series: pd.Series, limits: float = 0.01) -> pd.Series:
        """1% Winsorize 极值处理"""
        if series.empty or series.isna().all():
            return series
        lower = series.quantile(limits)
        upper = series.quantile(1 - limits)
        return series.clip(lower, upper)

    def compute_zscore(self, series: pd.Series, window: int = 60) -> pd.Series:
        """计算滚动 Z-Score"""
        if len(series) < window:
            return pd.Series([np.nan] * len(series), index=series.index)
        mu = series.rolling(window=window, min_periods=window//2).mean()
        sigma = series.rolling(window=window, min_periods=window//2).std()
        return (series - mu) / sigma
