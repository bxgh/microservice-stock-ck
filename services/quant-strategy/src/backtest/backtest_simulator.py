
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from adapters.clickhouse_loader import ClickHouseLoader
from backtest.analyzer import PerformanceAnalyzer
from backtest.models import BacktestConfig, BacktestResult, TradeRecord
from core.analysis.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

class BacktestSimulator:
    """
    高精度策略回测模拟器 (Epic Part 3)
    支持 Walk-Forward Analysis 与基于资金团的信号仿真。
    """
    def __init__(self, loader: ClickHouseLoader | None = None, analysis_service: AnalysisService | None = None):
        self.loader = loader if loader else ClickHouseLoader()
        self.analysis_service = analysis_service if analysis_service else AnalysisService()

    async def initialize(self):
        await self.loader.initialize()
        await self.analysis_service.initialize()
        logger.info("🚀 BacktestSimulator initialized")

    async def run_walk_forward_backtest(
        self,
        start_date: str,
        end_date: str,
        train_window: int = 3,  # 训练窗口天数 (用于聚类分析)
        test_window: int = 1,   # 测试窗口天数 (用于信号验证)
        config: BacktestConfig = BacktestConfig()
    ) -> list[BacktestResult]:
        """
        运行滚动窗口回测 (Walk-Forward)
        """
        logger.info(f"📅 Starting Walk-Forward Backtest from {start_date} to {end_date}")

        # 获取交易日列表 (从 ClickHouse 或外部配置加载)
        # 这里假设直接使用日期范围，实际应过滤 A 股交易日
        all_dates = pd.date_range(start=start_date, end=end_date, freq='B')
        date_strs = [d.strftime("%Y-%m-%d") for d in all_dates]

        results = []
        for i in range(train_window, len(date_strs), test_window):
            # 训练集: 前 train_window 天
            train_dates = date_strs[i-train_window:i]
            # 测试集: 之后 test_window 天
            test_dates = date_strs[i:i+test_window]

            if not test_dates:
                break

            logger.info(f"🔄 Rolling Window: Train={train_dates}, Test={test_dates}")

            # 1. 训练阶段: 加载或触发聚类分析
            # 在 Backtest 中，通常聚类已存入 ClickHouse
            last_train_date = train_dates[-1]
            clusters_df = await self.loader.get_analysis_results(last_train_date)

            if clusters_df.empty:
                logger.warning(f"No clusters found for training date {last_train_date}. Skipping.")
                continue

            # 2. 预测/验证阶段: 对 Test 窗口中的每一天运行信号仿真
            for t_date in test_dates:
                result = await self.simulate_test_day(t_date, clusters_df, config)
                if result:
                    results.append(result)

        return results

    async def simulate_test_day(
        self,
        trade_date: str,
        clusters_df: pd.DataFrame,
        config: BacktestConfig
    ) -> BacktestResult | None:
        """
        模拟单个测试日的信号触发与交易
        """
        logger.info(f"🧪 Simulating Test Day: {trade_date}")

        # 1. 加载测试日全量特征
        all_members = []
        for _, row in clusters_df.iterrows():
            all_members.extend(row['members'])
        all_members = sorted(set(all_members))

        from cache.feature_store import FeatureStore
        feature_store = FeatureStore()
        features_dict = await feature_store.batch_get(all_members, trade_date)

        if not features_dict:
            logger.warning(f"No features found for {trade_date}, skipping.")
            return None

        # 2. 交易状态维护
        capital = config.initial_capital
        positions = {} # stock_code -> {'volume': int, 'avg_price': float}
        trades = []
        equity_curve = []

        # 简化价格与成交量：
        # 假设 $P_0 = 1.0$，后续价格按收益率累乘
        # 假设 AvgVolume 为 1.0 (归一化)，OrderSize 比例进行滑点计算

        # 3. 分钟级仿真 (0-239)
        for t in range(240):
            # i. 信号产生
            signals = self._check_signals(t, clusters_df, features_dict)

            # ii. 执行交易
            for sig in signals:
                code = sig['code']
                if sig['type'] == 'BUY' and code not in positions:
                    # 模拟买入
                    # 滑点计算 (Kyle's Lambda 简化)
                    slippage = 0.0005 * np.sqrt(0.1) # 假定固定冲击
                    price = np.exp(np.sum(features_dict[code][:t+1, 2])) * (1 + slippage)

                    # 费率
                    cost = price * (1 + config.commission_rate)
                    # 简单分配：每个信号用 10% 资金
                    invest = capital * 0.1
                    volume = int(invest / cost)

                    if volume > 0:
                        capital -= volume * cost
                        positions[code] = {'volume': volume, 'entry_price': price, 'entry_t': t}
                        trades.append(TradeRecord(
                            stock_code=code, direction='BUY', price=price, volume=volume,
                            amount=volume*price, commission=volume*price*config.commission_rate,
                            tax=0, timestamp=datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(minutes=t),
                            strategy_id='EPIC-004-INTRA', reason=sig['reason']
                        ))

            # iii. 止损/止盈/收盘平仓检查
            for code in list(positions.keys()):
                pos = positions[code]
                current_price = np.exp(np.sum(features_dict[code][:t+1, 2]))
                pnl = (current_price / pos['entry_price']) - 1

                # 止损 2% 或收盘平仓
                if pnl < -0.02 or t == 239:
                    # 卖出
                    price = current_price * (1 - 0.0005) # 滑点
                    revenue = pos['volume'] * price * (1 - config.commission_rate - config.stamp_duty)
                    capital += revenue

                    trades.append(TradeRecord(
                        stock_code=code, direction='SELL', price=price, volume=pos['volume'],
                        amount=pos['volume']*price, commission=pos['volume']*price*config.commission_rate,
                        tax=pos['volume']*price*config.stamp_duty,
                        timestamp=datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(minutes=t),
                        strategy_id='EPIC-004-INTRA', reason='Exit',
                        realized_pnl=revenue - (pos['volume'] * pos['entry_price'])
                    ))
                    del positions[code]

            # iv. 结算净值
            market_value = sum([pos['volume'] * np.exp(np.sum(features_dict[c][:t+1, 2])) for c, pos in positions.items()])
            timestamp = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(minutes=t)
            equity_curve.append({'date': timestamp, 'value': capital + market_value})

        # 4. 计算当日绩效
        equity_df = pd.DataFrame(equity_curve)
        equity_df['returns'] = equity_df['value'].pct_change().fillna(0)

        # 加载基准 (假定同步加载，实际可从 AnalysisService 逻辑复用)
        # 这里简化：从 AnalysisService 获取基准收益向量
        benchmark_returns_vec = await self.analysis_service._get_benchmark_returns(trade_date, "000300")
        bench_series = pd.Series(benchmark_returns_vec, index=equity_df.index) if benchmark_returns_vec is not None else None

        metrics = PerformanceAnalyzer.calculate(
            equity_curve, trades, config.risk_free_rate, benchmark_returns=bench_series
        )

        return BacktestResult(
            strategy_id='EPIC-004-INTRA', stock_code='CLUSTER_MODE',
            start_date=datetime.strptime(trade_date, "%Y-%m-%d"),
            end_date=datetime.strptime(trade_date, "%Y-%m-%d"),
            initial_capital=config.initial_capital, final_capital=equity_df['value'].iloc[-1],
            metrics=metrics, equity_curve=equity_curve, trades=trades, config=config
        )

    def _check_signals(self, t: int, clusters_df: pd.DataFrame, features: dict[str, np.ndarray]) -> list[dict]:
        """
        检查 T 时刻的信号触发
        """
        signals = []

        for _, cluster in clusters_df.iterrows():
            members = cluster['members']
            leaders = [L[0] for L in cluster['leaders'][:2]] # 取前两个龙头

            # 信号 1: LAG_CATCHUP (补涨拦截)
            # 逻辑：龙头在 T 时刻之前的 5 分钟内涨幅超过 1%，而跟着涨幅小于 0.2% 且 OBI 变正
            for leader in leaders:
                if leader not in features: continue
                leader_feat = features[leader]

                # 计算最近 5 分钟收益 (Column 2 is Returns)
                if t < 5: continue
                leader_move = np.sum(leader_feat[t-5:t, 2])

                if leader_move > 0.01: # 龙头起飞
                    for m in members:
                        if m == leader or m not in features: continue
                        m_feat = features[m]
                        m_move = np.sum(m_feat[t-5:t, 2])
                        m_obi = m_feat[t, 1] # Column 1 is OBI

                        if m_move < 0.002 and m_obi > 0.5:
                            signals.append({
                                'type': 'BUY',
                                'code': m,
                                'reason': f'LAG_CATCHUP: Leader {leader} move {leader_move:.4f}',
                                't': t
                            })

            # 信号 2: GAP_FOLLOW (龙头高开追涨)
            if t == 5: # 开盘 5 分钟检查
                for leader in leaders:
                    if leader not in features: continue
                    l_feat = features[leader]
                    # 假定第一个收益率点反映了开盘跳空
                    gap = l_feat[0, 2]
                    vol_ratio = np.mean(l_feat[0:5, 4]) / 1.0 # 假设 Column 4 是 Volume 归一化后的
                    if gap > 0.02 and vol_ratio > 2.0:
                        signals.append({
                            'type': 'BUY',
                            'code': leader,
                            'reason': f'GAP_FOLLOW: Gap {gap:.4f}',
                            't': t
                        })

        return signals

    async def close(self):
        await self.loader.close()
        await self.analysis_service.close()
