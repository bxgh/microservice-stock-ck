#!/usr/bin/env python3
"""
分笔数据完整性校验脚本

功能：
1. 对比K线与分笔数据，识别缺失股票
2. 自动排除指数（399XXX系列）
3. 自动排除停牌股（成交量=0）
4. 输出需要补采的股票代码列表

用法：
    python3 validate_tick_coverage.py --date 20260116
    python3 validate_tick_coverage.py --date 20260116 --output /path/to/missing_codes.txt
"""

import argparse
import subprocess
import sys
from typing import List, Tuple, Set
from datetime import datetime


class TickCoverageValidator:
    """分笔数据覆盖率校验器"""
    
    def __init__(self, trade_date: str):
        """
        初始化校验器
        
        Args:
            trade_date: 交易日期，格式 YYYYMMDD 或 YYYY-MM-DD
        """
        self.trade_date = self._normalize_date(trade_date)
        self.clickhouse_cmd = [
            'docker', 'exec', '-i', 'microservice-stock-clickhouse',
            'clickhouse-client', '-u', 'admin', '--password', 'admin123', '-q'
        ]
    
    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """标准化日期格式为 YYYY-MM-DD"""
        date_str = date_str.replace('-', '')
        if len(date_str) == 8:
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        raise ValueError(f"Invalid date format: {date_str}")
    
    def _query(self, sql: str) -> str:
        """执行ClickHouse查询"""
        cmd = self.clickhouse_cmd + [sql]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    
    def get_kline_stocks(self) -> Set[str]:
        """
        获取K线股票列表（标准化6位代码）
        
        Returns:
            标准化后的股票代码集合
        """
        sql = f"""
        SELECT DISTINCT substring(stock_code, 4) as code
        FROM stock_data.stock_kline_daily
        WHERE trade_date = '{self.trade_date}'
        ORDER BY code
        """
        result = self._query(sql)
        return set(result.split('\n')) if result else set()
    
    def get_tick_stocks(self) -> Set[str]:
        """
        获取分笔股票列表
        
        Returns:
            股票代码集合
        """
        sql = f"""
        SELECT DISTINCT stock_code
        FROM stock_data.tick_data
        WHERE trade_date = '{self.trade_date}'
        ORDER BY stock_code
        """
        result = self._query(sql)
        return set(result.split('\n')) if result else set()
    
    def get_stock_volume(self, stock_code: str) -> float:
        """
        获取股票成交量
        
        Args:
            stock_code: 6位股票代码
            
        Returns:
            成交量
        """
        sql = f"""
        SELECT volume
        FROM stock_data.stock_kline_daily
        WHERE trade_date = '{self.trade_date}'
          AND substring(stock_code, 4) = '{stock_code}'
        """
        result = self._query(sql)
        return float(result) if result else 0.0
    
    def validate(self) -> Tuple[List[str], dict]:
        """
        执行完整校验
        
        Returns:
            (need_补采的股票列表, 统计信息字典)
        """
        print(f"[1/5] 获取K线股票列表...")
        kline_stocks = self.get_kline_stocks()
        print(f"      K线唯一股票数: {len(kline_stocks)}")
        
        print(f"[2/5] 获取分笔股票列表...")
        tick_stocks = self.get_tick_stocks()
        print(f"      分笔唯一股票数: {len(tick_stocks)}")
        
        print(f"[3/5] 计算缺口...")
        gap_stocks = kline_stocks - tick_stocks
        print(f"      初始缺口数: {len(gap_stocks)}")
        
        print(f"[4/5] 分类筛选...")
        indexes = []
        suspended = []
        need_collect = []
        
        for code in sorted(gap_stocks):
            # 排除深交所指数
            if code.startswith('399'):
                indexes.append(code)
                continue
            
            # 排除上交所指数
            if code in ['000001', '000016', '000300', '000688', '000905', '000852']:
                indexes.append(code)
                continue
            
            # 查询成交量
            volume = self.get_stock_volume(code)
            
            if volume == 0:
                suspended.append(code)
            else:
                need_collect.append((code, volume))
        
        # 按成交量排序
        need_collect.sort(key=lambda x: x[1], reverse=True)
        need_collect_codes = [code for code, _ in need_collect]
        
        stats = {
            'kline_total': len(kline_stocks),
            'tick_total': len(tick_stocks),
            'gap_total': len(gap_stocks),
            'indexes': len(indexes),
            'suspended': len(suspended),
            'need_collect': len(need_collect_codes)
        }
        
        print(f"[5/5] 分类完成:")
        print(f"      - 指数: {stats['indexes']}")
        print(f"      - 停牌股: {stats['suspended']}")
        print(f"      - 需要补采: {stats['need_collect']}")
        print()
        
        return need_collect_codes, stats


def main():
    parser = argparse.ArgumentParser(
        description='分笔数据完整性校验',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 校验指定日期
    python3 validate_tick_coverage.py --date 20260116
    
    # 输出到文件
    python3 validate_tick_coverage.py --date 20260116 --output missing_codes.txt
        """
    )
    parser.add_argument('--date', required=True, help='交易日期 (YYYYMMDD 或 YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='输出文件路径（可选）')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    try:
        # 执行校验
        validator = TickCoverageValidator(args.date)
        print(f"=" * 60)
        print(f"分笔数据完整性校验 - {validator.trade_date}")
        print(f"=" * 60)
        print()
        
        need_collect, stats = validator.validate()
        
        # 输出结果
        print("=" * 60)
        print("校验结果汇总")
        print("=" * 60)
        print(f"K线股票数:   {stats['kline_total']}")
        print(f"分笔股票数:  {stats['tick_total']}")
        print(f"数据覆盖率:  {stats['tick_total'] / stats['kline_total'] * 100:.2f}%")
        print()
        print(f"缺口总数:    {stats['gap_total']}")
        print(f"  - 指数:    {stats['indexes']} (无需补采)")
        print(f"  - 停牌股:  {stats['suspended']} (无需补采)")
        print(f"  - 需补采:  {stats['need_collect']}")
        print()
        
        if need_collect:
            print("需要补采的股票代码:")
            if args.verbose:
                for code in need_collect:
                    print(f"  {code}")
            else:
                print(f"  {', '.join(need_collect[:10])}")
                if len(need_collect) > 10:
                    print(f"  ... 及其他 {len(need_collect) - 10} 只")
            print()
            
            # 写入文件
            if args.output:
                with open(args.output, 'w') as f:
                    for code in need_collect:
                        f.write(f"{code}\n")
                print(f"✓ 股票代码已保存到: {args.output}")
            else:
                print("提示: 使用 --output 参数保存股票列表到文件")
        else:
            print("✓ 数据完整，无需补采")
        
        print()
        return 0
        
    except Exception as e:
        print(f"✗ 校验失败: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
