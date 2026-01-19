#!/usr/bin/env python3
import asyncio, sys
sys.path.insert(0, '/app/src')
from database import init_database, close_database, get_session, StrategyConfig, StrategySignal, BacktestRecord
from sqlalchemy import select
from datetime import datetime

async def main():
    print("\n" + "="*60)
    print("COMPREHENSIVE DATABASE TEST")
    print("="*60 + "\n")
    
    # Test 1: Init
    print("[Test 1] Database Initialization...")
    await init_database()
    print("✅ Database initialized\n")
    
    # Test 2: Create StrategyConfig
    print("[Test 2] Creating Strategy Configs...")
    async for session in get_session():
        configs = [
            StrategyConfig(strategy_name="OFI", strategy_type="OFI", parameters={"threshold": 0.5}, enabled=True),
            StrategyConfig(strategy_name="SmartMoney", strategy_type="SmartMoney", parameters={"min_size": 1000}, enabled=True)
        ]
        for c in configs:
            session.add(c)
    print(f"✅ Created {len(configs)} configs\n")
    
    # Test 3: Read StrategyConfig
    print("[Test 3] Reading Strategy Configs...")
    async for session in get_session():
        result = await session.execute(select(StrategyConfig))
        all_configs = result.scalars().all()
        print(f"✅ Found {len(all_configs)} configs:")
        for c in all_configs:
            print(f"   - {c.strategy_name} ({c.strategy_type}): {c.parameters}")
    print()
    
    # Test 4: Create Signals
    print("[Test 4] Creating Strategy Signals...")
    async for session in get_session():
        signals = [
            StrategySignal(strategy_name="OFI", stock_code="600519", signal_type="LONG", priority="HIGH", price=1850.0, score=85.0),
            StrategySignal(strategy_name="SmartMoney", stock_code="000001", signal_type="LONG", priority="MEDIUM", price=12.5, score=72.0)
        ]
        for s in signals:
            session.add(s)
    print(f"✅ Created {len(signals)} signals\n")
    
    # Test 5: Read Signals
    print("[Test 5] Reading Signals...")
    async for session in get_session():
        result = await session.execute(select(StrategySignal))
        all_signals = result.scalars().all()
        print(f"✅ Found {len(all_signals)} signals:")
        for s in all_signals:
            print(f"   - {s.strategy_name} → {s.stock_code}: {s.signal_type} (score={s.score})")
    print()
    
    # Test 6: Create Backtest
    print("[Test 6] Creating Backtest Records...")
    async for session in get_session():
        bt = BacktestRecord(
            strategy_name="OFI",
            backtest_name="2024_Q1",
            period_start=datetime(2024,1,1),
            period_end=datetime(2024,3,31),
            initial_capital=100000,
            final_capital=115000,
            total_return=0.15,
            max_drawdown=0.08,
            sharpe_ratio=1.85,
            win_rate=0.62,
            total_signals=150
        )
        session.add(bt)
    print("✅ Created backtest record\n")
    
    # Test 7: Read Backtest
    print("[Test 7] Reading Backtest Records...")
    async for session in get_session():
        result = await session.execute(select(BacktestRecord))
        all_bt = result.scalars().all()
        print(f"✅ Found {len(all_bt)} backtest records:")
        for bt in all_bt:
            print(f"   - {bt.strategy_name} ({bt.backtest_name}): Return={bt.total_return:.1%}, Sharpe={bt.sharpe_ratio:.2f}")
    print()
    
    # Cleanup
    print("[Test 8] Cleanup...")
    await close_database()
    print("✅ Database connections closed\n")
    
    print("="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)

asyncio.run(main())
