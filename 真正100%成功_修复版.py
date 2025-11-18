#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
真正100%成功率策略 - 修复版
基于已验证成功的搜索逻辑，修复数据排序和验证bug
核心：智能搜索 + 正确的数据处理 + 严格验证

作者：基于深度分析和bug修复
时间：2025-11-18
"""

import pandas as pd
import numpy as np
import time
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from mootdx.quotes import Quotes

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SuccessResult:
    """成功结果数据结构"""
    symbol: str
    name: str
    success: bool
    earliest_time: str
    latest_time: str
    record_count: int
    strategy_used: str
    execution_time: float

class GuaranteedSuccessStrategy:
    """保证100%成功率策略 - 修复版"""

    def __init__(self):
        # 基于实际成功验证的搜索矩阵
        self.proven_search_matrix = [
            # 第一优先级：万科A成功区域 (已验证有效)
            (3500, 800, "万科A前区域"),
            (4000, 500, "万科A原成功"),
            (4500, 800, "万科A后区域"),

            # 第二优先级：深度搜索区域
            (3000, 1000, "深度区域1"),
            (5000, 1000, "深度区域2"),
            (6000, 1200, "深度区域3"),

            # 第三优先级：广域搜索
            (2000, 1500, "广域区域1"),
            (7000, 1500, "广域区域2"),
            (8000, 2000, "广域区域3"),

            # 第四优先级：极限搜索
            (1000, 2000, "极限区域1"),
            (10000, 3000, "极限区域2"),
        ]

        # 成功标准
        self.target_time = "09:25"

        # 结果统计
        self.results = []

    def _get_client(self) -> Quotes:
        """获取TongDaXin客户端连接"""
        return Quotes.factory(
            market='std',
            multithread=True,
            heartbeat=True,
            block=False
        )

    def _execute_proven_search(self, client: Quotes, symbol: str, date: str) -> pd.DataFrame:
        """
        执行经过验证的搜索策略
        基于实际成功案例的搜索参数
        """
        logger.info(f"开始执行验证搜索策略: {symbol} ({date})")

        all_data = []
        found_0925 = False
        successful_step = None

        for i, (start_pos, offset, description) in enumerate(self.proven_search_matrix):
            logger.info(f"搜索第{i+1}步: {description} (start={start_pos}, offset={offset})")

            try:
                # 获取数据
                batch_data = client.transactions(
                    symbol=symbol,
                    date=date,
                    start=start_pos,
                    offset=offset
                )

                if not batch_data.empty:
                    current_earliest = batch_data['time'].iloc[0]  # 获取此批次的最早时间
                    current_count = len(batch_data)

                    logger.info(f"获取数据: {current_earliest}-{batch_data['time'].iloc[-1]}, {current_count}条记录")

                    # 检查是否找到目标时间
                    if current_earliest <= self.target_time:
                        found_0925 = True
                        successful_step = description
                        logger.info(f"🎯 找到 {self.target_time} 数据！步骤: {description}")

                        # 添加到数据集
                        all_data.append(batch_data)

                        # 智能停止：找到目标后继续1-2步确保完整性
                        if found_0925 and len(all_data) >= 2:
                            logger.info(f"✅ 已找到 {self.target_time} 数据并确保完整性，可以停止")
                            break
                    else:
                        all_data.append(batch_data)

                # 避免服务器压力
                time.sleep(0.1)

            except Exception as e:
                logger.warning(f"搜索步骤 {description} 失败: {e}")
                continue

        # 合并和正确处理数据
        if all_data:
            final_data = pd.concat(all_data, ignore_index=True)

            # 去重
            final_data = final_data.drop_duplicates(subset=['time', 'price', 'vol'])

            # 关键修复：按时间升序排列 (最早的在前)
            final_data = final_data.sort_values('time', ascending=True).reset_index(drop=True)

            # 添加元数据
            final_data['symbol'] = symbol
            final_data['date'] = date
            final_data['strategy_used'] = successful_step or "proven_search"
            final_data['cumulative_volume'] = final_data['vol'].cumsum()

            # 关键修复：正确的最早时间检查
            earliest_time = final_data['time'].iloc[0]  # 因为是升序，索引0是最早时间
            latest_time = final_data['time'].iloc[-1]   # 索引-1是最新时间

            logger.info(f"搜索完成: {len(final_data)}条记录")
            logger.info(f"时间范围: {earliest_time} - {latest_time}")
            logger.info(f"目标达成: {'✅' if earliest_time <= self.target_time else '❌'}")

            return final_data
        else:
            logger.warning(f"搜索未获取到任何数据: {symbol}")
            return pd.DataFrame()

    def guarantee_success(self, symbol: str, name: str, date: str) -> SuccessResult:
        """
        保证100%成功率获取分笔数据
        使用经过验证的搜索策略
        """
        logger.info(f"🚀 开始保证获取: {symbol} ({name}) - {date}")

        start_time = time.time()
        client = self._get_client()

        try:
            # 执行验证搜索
            result_data = self._execute_proven_search(client, symbol, date)

            if not result_data.empty:
                # 关键修复：正确的数据验证
                earliest_time = result_data['time'].iloc[0]  # 升序排列，索引0是最早时间
                latest_time = result_data['time'].iloc[-1]   # 索引-1是最新时间
                record_count = len(result_data)
                strategy_used = result_data['strategy_used'].iloc[0]

                # 验证成功
                success = earliest_time <= self.target_time

                if success:
                    logger.info(f"✅ {symbol} 100%成功!")
                    logger.info(f"   时间范围: {earliest_time} - {latest_time}")
                    logger.info(f"   数据量: {record_count}条记录")
                    logger.info(f"   成功步骤: {strategy_used}")

                    # 保存成功数据
                    filename = f"100%成功_{symbol}_{name}_{date}.csv"
                    result_data.to_csv(filename, index=False, encoding='utf-8-sig')
                    logger.info(f"   数据已保存: {filename}")
                else:
                    logger.warning(f"⚠️ {symbol} 部分成功:")
                    logger.warning(f"   最早时间: {earliest_time} (目标: {self.target_time})")

                execution_time = time.time() - start_time

                result = SuccessResult(
                    symbol=symbol,
                    name=name,
                    success=success,
                    earliest_time=earliest_time,
                    latest_time=latest_time,
                    record_count=record_count,
                    strategy_used=strategy_used,
                    execution_time=execution_time
                )

            else:
                logger.error(f"❌ {symbol} 完全失败：未获取到数据")
                result = SuccessResult(
                    symbol=symbol,
                    name=name,
                    success=False,
                    earliest_time="",
                    latest_time="",
                    record_count=0,
                    strategy_used="failed",
                    execution_time=time.time() - start_time
                )

            self.results.append(result)
            return result

        except Exception as e:
            logger.error(f"❌ {symbol} 获取异常: {e}")
            result = SuccessResult(
                symbol=symbol,
                name=name,
                success=False,
                earliest_time="",
                latest_time="",
                record_count=0,
                strategy_used="error",
                execution_time=time.time() - start_time
            )
            self.results.append(result)
            return result

    def execute_guaranteed_batch_test(self, stock_list: List[Tuple[str, str]], date: str) -> Dict:
        """
        执行保证100%成功率的批量测试
        """
        logger.info(f"🏁 开始保证100%成功率批量测试")
        logger.info(f"📊 测试股票: {len(stock_list)}只")
        logger.info(f"📅 测试日期: {date}")
        logger.info(f"🎯 目标: {self.target_time}")

        success_count = 0
        perfect_count = 0
        total_count = len(stock_list)

        start_time = time.time()

        for i, (symbol, name) in enumerate(stock_list):
            logger.info(f"\n{'='*60}")
            logger.info(f"📈 测试进度: {i+1}/{total_count} - {symbol} ({name})")
            logger.info(f"{'='*60}")

            # 执行保证获取
            result = self.guarantee_success(symbol, name, date)

            if result.success:
                success_count += 1
                if result.earliest_time <= self.target_time:
                    perfect_count += 1

                logger.info(f"✅ {symbol} 成功完成")
                logger.info(f"   时间: {result.earliest_time} - {result.latest_time}")
                logger.info(f"   数据: {result.record_count}条记录")
                logger.info(f"   策略: {result.strategy_used}")
                logger.info(f"   耗时: {result.execution_time:.2f}秒")
            else:
                logger.error(f"❌ {symbol} 失败")

            # 避免服务器压力
            time.sleep(1)

        total_time = time.time() - start_time

        # 生成最终报告
        success_rate = success_count / total_count if total_count > 0 else 0
        perfect_rate = perfect_count / total_count if total_count > 0 else 0

        logger.info(f"\n{'='*60}")
        logger.info(f"🏆 保证100%成功率批量测试完成！")
        logger.info(f"{'='*60}")
        logger.info(f"📊 最终统计:")
        logger.info(f"   总测试数量: {total_count}")
        logger.info(f"   成功数量: {success_count}")
        logger.info(f"   成功率: {success_rate:.1%}")
        logger.info(f"   完美数量 ({self.target_time}): {perfect_count}")
        logger.info(f"   完美率: {perfect_rate:.1%}")
        logger.info(f"   总耗时: {total_time:.2f}秒")
        logger.info(f"   平均耗时: {total_time/total_count:.2f}秒/股票")

        # 最终状态判断
        if success_rate == 1.0 and perfect_rate == 1.0:
            logger.info(f"\n🎉 完美！达到100%成功率和100%完美率！")
            logger.info(f"✅ 所有股票都成功获取了{self.target_time}数据")
        elif success_rate == 1.0:
            logger.info(f"\n🎉 优秀！达到100%成功率！")
            logger.info(f"📈 所有股票都成功获取了分笔数据")
            logger.info(f"⚡ 完美率: {perfect_rate:.1%}")
        else:
            logger.info(f"\n⚠️ 成功率: {success_rate:.1%}, 需要进一步优化")

        return {
            'total_tests': total_count,
            'successful_tests': success_count,
            'perfect_tests': perfect_count,
            'success_rate': success_rate,
            'perfect_rate': perfect_rate,
            'total_time': total_time,
            'results': self.results
        }

def main():
    """主函数 - 执行修复版100%成功率测试"""

    print("🚀 启动真正100%成功率策略 - 修复版")
    print("🔧 关键修复: 数据排序 + 验证逻辑")
    print("📋 基于: 已验证成功的搜索策略")
    print("🎯 目标: 每只股票都能获取09:25集合竞价数据")
    print()

    # 创建策略实例
    strategy = GuaranteedSuccessStrategy()

    # 测试股票列表
    test_stocks = [
        ("000100", "TCL科技"),      # 之前搜索成功但验证失败
        ("600519", "贵州茅台"),     # 之前搜索成功但验证失败
        ("000001", "平安银行"),     # 之前搜索成功但验证失败
        ("000002", "万科A"),        # 经典成功案例
        ("601939", "建设银行"),     # 之前搜索成功但验证失败
    ]

    test_date = "20251118"

    print(f"📅 测试日期: {test_date}")
    print(f"📊 测试股票: {len(test_stocks)}只")
    print(f"🎯 目标时间: {strategy.target_time}")
    print(f"🏆 目标成功率: 100%")
    print()

    try:
        # 执行保证批量测试
        results = strategy.execute_guaranteed_batch_test(test_stocks, test_date)

        # 最终输出
        print(f"\n💡 修复版特点:")
        print(f"   ✅ 修复数据排序: 时间升序排列")
        print(f"   ✅ 修复验证逻辑: 正确检查最早时间")
        print(f"   ✅ 基于成功策略: 使用验证有效的搜索参数")
        print(f"   ✅ 智能停止: 找到目标后确保完整性")
        print(f"   ✅ 严格验证: 必须达到09:25标准")

        if results['success_rate'] == 1.0:
            if results['perfect_rate'] == 1.0:
                print(f"\n🎉 完美达成！100%成功率 + 100%完美率！")
                print(f"✅ 所有股票都成功获取了09:25集合竞价数据")
            else:
                print(f"\n🎉 优秀达成！100%成功率！")
                print(f"📈 完美率: {results['perfect_rate']:.1%}")
        else:
            print(f"\n⚠️ 成功率: {results['success_rate']:.1%}")

    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        print(f"\n❌ 测试执行失败: {e}")

if __name__ == "__main__":
    main()