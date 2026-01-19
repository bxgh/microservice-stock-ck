"""
数据校验规则配置模块

集中管理所有数据类型的校验阈值，实现规则与业务逻辑的解耦。
"""


class TickStandards:
    """
    分笔数据校验标准
    
    分为宽松标准 (采集过滤) 和严格标准 (盘后审计) 两个级别。
    """
    
    class Loose:
        """
        宽松标准 - 用于采集时的快速判断
        
        目标: 判断数据是否"基本存在"，避免重复采集
        """
        MIN_TIME = "10:00:00"   # 首笔时间上限
        MAX_TIME = "14:30:00"   # 末笔时间下限
        MIN_COUNT = 2000        # 最小 Tick 数量
    
    class IntradayRealtime:
        """
        盘中实时数据校验 (tick_data_intraday)
        
        用于盘中监控，校验标准随时间动态变化。
        """
        # 盘中只需要保证数据"新鲜"，不做完整性强校验
        MAX_DELAY_SECONDS = 180         # 最大允许延迟3分钟
        
    class IntradayPostMarket:
        """
        盘后当日数据校验 (tick_data_intraday)
        
        用于当日收盘后的数据审计 (Gate-3)。
        不允许大幅度缺失，但容忍少量网络抖动。
        """
        MIN_TIME = "09:25:00"           
        MAX_TIME = "15:00:00"
        MIN_ACTIVE_MINUTES = 230        # 稍宽松
        PRICE_TOLERANCE = 0.02          # 2%
        VOLUME_TOLERANCE = 0.10         # 10%
        
    class History:
        """
        历史归档数据校验 (tick_data)
        
        要求高度完整和准确。
        """
        MIN_TIME = "09:25:05"
        MAX_TIME = "14:59:55"
        MIN_ACTIVE_MINUTES = 230        # 严格 (考虑集合竞价自然停顿，调优从 237 到 230)
        PRICE_TOLERANCE = 0.011         # 1.1%
        VOLUME_TOLERANCE = 0.05         # 5%

        
    # 交易时段常量
    STANDARD_TRADING_MINUTES = 241      # 一个完整交易日的分钟数
    # 09:25 (集合竞价) + 09:30-11:30 (120分钟) + 13:00-15:00 (120分钟) = 241


class KLineStandards:
    """
    K线数据校验标准
    """
    # 覆盖率
    MIN_COVERAGE_RATE = 98.0            # 最低覆盖率 (%)
    
    # 连续性
    MAX_GAP_DAYS = 10                   # 最大允许缺口天数 (排除停牌)
    
    # OHLC 合理性
    OHLC_RULES = {
        "high_ge_low": True,            # high >= low
        "high_ge_open": True,           # high >= open
        "high_ge_close": True,          # high >= close
        "low_le_open": True,            # low <= open
        "low_le_close": True,           # low <= close
    }
    
    # 涨跌幅阈值 (用于异常检测)
    MAX_DAILY_CHANGE_RATE = 20.0        # 最大日涨跌幅 (%)，超过视为异常数据


class StockListStandards:
    """
    股票名单校验标准
    """
    # 数量范围
    MIN_COUNT = 4500                    # 最小股票数量
    MAX_COUNT = 6000                    # 最大股票数量
    FALLBACK_COUNT = 5499               # 降级兜底数量
    
    # A股代码前缀规则
    SH_PREFIXES = ("600", "601", "603", "605", "688")  # 沪市
    SZ_PREFIXES = ("000", "001", "002", "003", "300", "301")  # 深市
    
    # 增量校验
    MAX_DAILY_CHANGE_RATIO = 0.02       # 日变动比例上限 (2%)
    MIN_OVERLAP_RATIO = 0.95            # 与前日最小重叠率 (95%)


class MarketStandards:
    """
    全市场级别校验标准
    """
    MIN_KLINE_COVERAGE_RATE = 98.0      # 全市场 K线覆盖率阈值
    MIN_TICK_COVERAGE_RATE = 95.0       # 全市场 分笔覆盖率阈值
    MAX_ABNORMAL_STOCKS = 500           # 允许的最大异常股票数量
