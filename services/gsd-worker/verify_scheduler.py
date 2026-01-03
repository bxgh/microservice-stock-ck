#!/usr/bin/env python3
"""
自适应调度器功能验证脚本

用于快速验证调度器的基本功能（不需要完整的Docker环境）
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock
import pytz

from core.adaptive_scheduler import AdaptiveKLineSyncScheduler

CST = pytz.timezone('Asia/Shanghai')


async def test_basic_functionality():
    """测试基本功能"""
    print("=" * 80)
    print("自适应调度器功能验证")
    print("=" * 80)
    
    # 创建Mock MySQL连接池
    pool = AsyncMock()
    conn = AsyncMock()
    cursor = AsyncMock()
    
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None
    conn.cursor.return_value.__aenter__.return_value = cursor
    conn.cursor.return_value.__aexit__.return_value = None
    
    # Mock历史记录查询
    yesterday = datetime.now(CST).replace(hour=18, minute=55, second=0, microsecond=0)
    cursor.fetchone.return_value = {
        'updated_at': yesterday,
        'total_records': 5000
    }
    
    # 创建调度器
    scheduler = AdaptiveKLineSyncScheduler(pool)
    
    # 测试1: 历史预测
    print("\n[测试1] 历史预测阶段")
    print("-" * 80)
    target_window = await scheduler.predict_wait_window()
    if target_window:
        print(f"✅ 成功计算目标观察窗口: {target_window.strftime('%H:%M:%S')}")
    else:
        print("❌ 未能计算目标观察窗口")
        return False
    
    # 测试2: 今日信号检查
    print("\n[测试2] 今日信号检查")
    print("-" * 80)
    
    # Mock今日信号查询
    cursor.fetchone.return_value = {
        'status': 'completed',
        'total_records': 5000,
        'updated_at': datetime.now(CST),
        'error_message': None
    }
    
    signal = await scheduler._check_today_signal()
    if signal and signal['status'] == 'completed':
        print(f"✅ 成功检测到completed信号: {signal['total_records']} 条记录")
    else:
        print("❌ 未能检测到信号")
        return False
    
    # 测试3: 配置参数加载
    print("\n[测试3] 配置参数加载")
    print("-" * 80)
    print(f"  历史缓冲时间: {scheduler.history_buffer_min} 分钟")
    print(f"  轮询间隔: {scheduler.poll_interval_min} 分钟")
    print(f"  最小记录数: {scheduler.min_records}")
    print(f"  超时时间: {scheduler.timeout_time_str}")
    print("✅ 配置参数加载正常")
    
    print("\n" + "=" * 80)
    print("✅ 所有基本功能测试通过！")
    print("=" * 80)
    return True


if __name__ == "__main__":
    result = asyncio.run(test_basic_functionality())
    sys.exit(0 if result else 1)
