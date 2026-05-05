from datetime import datetime, timedelta

from backtest.cross_sectional_simulator import VirtualPortfolio
from models.signal import Signal, SignalType, Priority
import pytz


def test_virtual_portfolio_open_logic():
    vp = VirtualPortfolio(initial_capital=100_000, commission=0.001, stamp_duty=0.001)

    # 构建某天的三个推荐股票
    cst = pytz.timezone('Asia/Shanghai')
    now = datetime.now(cst)
    signals = [
        Signal.create(stock_code="000001", signal_type=SignalType.LONG, price=0, score=100.0, priority=Priority.HIGH, strategy_name="T1", reason="R1"),
        Signal.create(stock_code="600000", signal_type=SignalType.LONG, price=0, score=100.0, priority=Priority.HIGH, strategy_name="T1", reason="R1"),
    ]

    # 次日开盘价
    prices = {
        "000001": 10.50,
        "600000": 20.20,
        "000002": 15.00 # 未推荐
    }

    # 执行买入: 留 5% 现金(5000), 用 95000 买，每只分配 47500。且不能超过单只 10000 的最大风控
    vp.open_positions(datetime.today(), signals, prices, max_weight=0.1)

    # 由于 max_weight 是 10%，因此理想分配 47500 被截断到 10000
    # 对于 000001 (10.5): 10000 / 10.5 = 952股 -> 降至 900 股
    assert "000001" in vp.positions
    assert vp.positions["000001"][0] == 900
    assert vp.positions["000001"][1] == 10.50

    # 对于 600000 (20.20): 10000 / 20.2 = 495股 -> 降至 400 股
    assert "600000" in vp.positions
    assert vp.positions["600000"][0] == 400

    # 核算成本金额
    cost_a = 900 * 10.50 * 1.001
    cost_b = 400 * 20.20 * 1.001
    assert abs(vp.cash - (100_000 - cost_a - cost_b)) < 0.01

def test_virtual_portfolio_close_and_mark_to_market():
    vp = VirtualPortfolio(initial_capital=100_000, commission=0.0, stamp_duty=0.0) # 免手续费测纯利润

    # 模拟手持仓位
    vp.positions["000001"] = (1000, 10.0)
    vp.cash = 90_000

    vp.mark_to_market(datetime.today(), {"000001": 11.0})
    # 90000 + 1000 * 11.0 = 101_000
    assert len(vp.equity_curve) == 1
    assert vp.equity_curve[0]["value"] == 101_000

    # T+1 卖出，当前市场价 12.0
    vp.close_all_positions(datetime.today() + timedelta(days=1), {"000001": 12.0})

    # 卖得 12000
    assert vp.cash == 90_000 + 12_000
    assert "000001" not in vp.positions
    assert len(vp.trade_history) == 1
    assert vp.trade_history[0].realized_pnl == 2_000
