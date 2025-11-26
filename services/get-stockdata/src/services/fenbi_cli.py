#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fenbi CLI
基于FenbiEngine的命令行界面，提供用户友好的分笔数据获取工具
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import List

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .fenbi_engine import FenbiEngine
except ImportError:
    from fenbi_engine import FenbiEngine


class FenbiCLI:
    """Fenbi命令行界面，提供用户友好的CLI交互"""

    def __init__(self):
        self.engine = None

    async def run(self, args):
        """运行CLI命令"""
        # 创建引擎
        try:
            self.engine = FenbiEngine("mootdx")
        except Exception as e:
            print(f"[ERROR] 初始化引擎失败: {e}")
            return 1

        try:
            # 获取数据
            print("=" * 60)
            print("Fenbi数据获取工具 (新架构)")
            print("=" * 60)
            print(f"股票代码: {args.symbol}")
            print(f"交易日期: {args.date}")
            print(f"数据源: {self.engine.data_source.source_name}")

            data = await self.engine.get_tick_data(args.symbol, args.date)

            if data:
                print(f"\n[OK] 数据获取成功!")
                print(f"总记录数: {len(data):,}")

                # 显示处理统计
                stats = self.engine.get_stats()
                if 'duration' in stats:
                    print(f"执行用时: {stats['duration']:.2f} 秒")

                # 显示数据处理信息
                if stats.get('duplicates_removed', 0) > 0:
                    print(f"去除重复: {stats['duplicates_removed']} 条")
                    print(f"唯一记录: {stats.get('unique_records', len(data)):,} 条")

                # 生成增强质量报告
                print("\n📊 开始数据质量分析...")
                enhanced_report = self.engine.generate_enhanced_report(data)

                # 基础质量信息
                basic_quality = enhanced_report['basic_quality']
                print(f"📈 数据完整性评分: {basic_quality['completeness_score']}/100")
                print(f"📈 时间覆盖度: {basic_quality['time_coverage']:.1%}")
                print(f"📈 数据质量评级: {basic_quality['quality_grade']}")

                # 统计分析
                stats_analysis = enhanced_report.get('statistical_analysis', {})
                if stats_analysis.get('price'):
                    price_stats = stats_analysis['price']
                    print(f"\n💰 价格统计:")
                    print(f"   均价: {price_stats['mean']:.2f}")
                    print(f"   最高: {price_stats['max']:.2f}")
                    print(f"   最低: {price_stats['min']:.2f}")
                    print(f"   标准差: {price_stats['std']:.4f}")

                if stats_analysis.get('volume'):
                    volume_stats = stats_analysis['volume']
                    print(f"\n📊 成交量统计:")
                    print(f"   平均成交量: {volume_stats['mean']:,.0f}")
                    print(f"   最大成交量: {volume_stats['max']:,.0f}")
                    print(f"   成交量总计: {volume_stats['sum']:,.0f}")

                # 数据特征
                data_chars = enhanced_report.get('data_characteristics', {})
                if data_chars.get('time_span'):
                    time_span = data_chars['time_span']
                    print(f"\n⏰ 时间范围: {time_span['start_time']} - {time_span['end_time']}")

                # 保存数据
                if args.format:
                    await self._save_data(data, args.symbol, args.date, args.format)

                return 0
            else:
                print(f"\n[ERROR] 未能获取到有效数据")
                if self.engine.stats['error_message']:
                    print(f"错误信息: {self.engine.stats['error_message']}")
                return 1

        except Exception as e:
            print(f"\n[ERROR] 程序执行出错: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1
        finally:
            if self.engine:
                await self.engine.close()

    async def _save_data(self, data, symbol: str, date: str, format_type: str):
        """
        保存数据到文件

        Args:
            data: 分笔数据
            symbol: 股票代码
            date: 日期
            format_type: 保存格式
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{symbol}_{date}_fenbi_transactions_{timestamp}"

        try:
            # 尝试导入导出工具
            try:
                from ..utils.file_exporter import export_to_csv, export_to_excel
            except ImportError:
                from utils.file_exporter import export_to_csv, export_to_excel

            if 'csv' in format_type:
                csv_filename = f"{base_filename}.csv"
                export_to_csv(data, csv_filename)
                file_size = os.path.getsize(csv_filename)
                print(f"[OK] CSV文件已保存: {csv_filename} ({file_size/1024:.1f} KB)")

            if 'excel' in format_type:
                excel_filename = f"{base_filename}.xlsx"
                export_to_excel(data, excel_filename)
                file_size = os.path.getsize(excel_filename)
                print(f"[OK] Excel文件已保存: {excel_filename} ({file_size/1024:.1f} KB)")

        except Exception as e:
            print(f"[ERROR] 文件保存失败: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Fenbi股票分笔数据获取工具 (新架构)')
    parser.add_argument('--symbol', required=True, help='股票代码 (例如: 000001)')
    parser.add_argument('--date', required=True, help='日期 (格式: YYYYMMDD)')
    parser.add_argument('--format', choices=['csv', 'excel', 'both'], default='both', help='输出格式')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')

    args = parser.parse_args()

    cli = FenbiCLI()
    return await cli.run(args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))