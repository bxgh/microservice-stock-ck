"""
Data Source Registry
数据源能力注册表和降级链配置

包含:
- CAPABILITIES: 数据源能力注册表
- FALLBACK_CHAINS: 降级链配置
"""
from typing import Dict, List

from .enums import DataSource, DataType
from .capability import DataSourceCapability


# ============================================================
# 数据源能力注册表
# ============================================================

CAPABILITIES: Dict[DataSource, DataSourceCapability] = {
    
    # --------------------------------------------------------
    # MOOTDX - 通达信直连
    # --------------------------------------------------------
    # 协议: 通达信私有TCP协议 (逆向工程)
    # 连接方式: 直连通达信行情服务器 (bestip自动选择最快节点)
    # 
    # 支持的接口:
    #   - quotes(symbol): 实时行情
    #       返回: code, name, open, high, low, price, bid1-5, ask1-5, volume, amount
    #   - transactions(symbol): 分笔成交
    #       返回: time, price, volume, type(买/卖/中性)
    #   - bars(symbol, frequency): 历史K线
    #       返回: date, open, high, low, close, volume, amount
    #       频率: 9=日线, 8=5分钟, 6=周线, 5=月线
    #       限制: 最多500条，无复权
    #   - stocks(market): 股票列表 (NEW)
    #       market: 0=深圳, 1=上海
    #       返回: 48,666 只股票
    #   - finance(symbol): 财务基础信息 (NEW)
    #       返回: 流通股本、总股本、省份、行业、上市日期
    #   - xdxr(symbol): 除权除息 (NEW)
    #       返回: 历史分红、送转股、配股记录
    #   - index_bars(symbol, frequency): 指数K线 (NEW)
    #       返回: 上证、深成、创业板指等指数历史数据
    #
    # 优势: 延迟最低(10-100ms)，无频率限制，无需外网，数据全面
    # 劣势: 无复权数据，历史数据有限(最多800条)，服务器可能不稳定
    # --------------------------------------------------------
    DataSource.MOOTDX: DataSourceCapability(
        name="mootdx",
        display_name="通达信直连",
        supported_types=(
            DataType.QUOTES, 
            DataType.TICK, 
            DataType.HISTORY, 
            DataType.STOCK_LIST,     # 新增
            DataType.FINANCE_INFO,   # 新增
            DataType.XDXR,           # 新增
            DataType.INDEX_BARS,     # 新增
        ),
        latency_ms=(10, 100),
        reliability=0.99,
        requires_network=False,
        rate_limit=0,
        notes="通达信TCP直连，延迟最低(10-100ms)，覆盖实时+历史+财务+除权；缺点：无复权，历史最多800条"
    ),
    
    # --------------------------------------------------------
    # EASYQUOTATION - 新浪/腾讯行情
    # --------------------------------------------------------
    # 协议: HTTP (新浪/腾讯公开接口)
    # 连接方式: HTTP请求 (需要外网或代理)
    #
    # 支持的接口:
    #   - stocks(codes): 批量获取实时行情
    #       返回: name, open, close, now, high, low, buy, sell, volume, amount
    #              bid1-5, ask1-5, date, time
    #
    # 优势: 接口稳定，数据格式清晰
    # 劣势: 需要外网访问，有频率限制(~60次/分钟)
    # --------------------------------------------------------
    DataSource.EASYQUOTATION: DataSourceCapability(
        name="easyquotation",
        display_name="新浪/腾讯行情",
        supported_types=(DataType.QUOTES,),
        latency_ms=(100, 500),
        reliability=0.95,
        requires_network=True,
        rate_limit=60,
        notes="新浪/腾讯HTTP接口，mootdx降级备选；缺点：依赖外网，频率限制"
    ),
    
    # --------------------------------------------------------
    # BAOSTOCK - 证券宝
    # --------------------------------------------------------
    # 协议: HTTP REST API (自建云端服务封装)
    # 数据来源: baostock.com (学术级开源量化数据)
    #
    # 支持的接口:
    #   - /api/v1/history/kline/{code}: 历史K线
    #       参数: start_date, end_date, frequency(d/w/m), adjust(1/2/3)
    #       返回: date, open, high, low, close, preclose, volume, amount, turn, pctChg
    #       复权: 1=后复权, 2=前复权, 3=不复权
    #   - /api/v1/index/cons/{index_code}: 指数成分股
    #       返回: updateDate, code, code_name
    #       支持: 沪深300(sz.399300), 上证50(sh.000016), 中证500(sz.000905)
    #   - /api/v1/industry/classify: 行业分类
    #       返回: code, code_name, industry, industryClassification
    #   - /api/v1/finance/profit/{code}: 盈利能力
    #       返回: pubDate, roeAvg, npMargin, gpMargin, netProfit, etc.
    #
    # 优势: 学术级数据质量，完整复权，指数成分准确
    # 劣势: 需登录，有频率限制(~30次/分钟)，数据更新略慢
    # --------------------------------------------------------
    DataSource.BAOSTOCK_API: DataSourceCapability(
        name="baostock-api",
        display_name="证券宝",
        supported_types=(DataType.HISTORY, DataType.INDEX, DataType.INDUSTRY, DataType.FINANCE),
        latency_ms=(500, 3000),
        reliability=0.95,
        requires_network=True,
        rate_limit=30,
        notes="学术级数据质量，完整复权(前复权/后复权/不复权)；缺点：需登录，有频率限制"
    ),
    
    # --------------------------------------------------------
    # AKSHARE - A股数据接口
    # --------------------------------------------------------
    # 协议: HTTP REST API (自建云端服务封装)
    # 数据来源: 东方财富、同花顺、新浪等多源聚合
    #
    # 支持的接口:
    #   - /api/v1/finance/{code}: 财务报表
    #       返回: 资产负债表、利润表、现金流量表核心指标
    #   - /api/v1/valuation/{code}: 估值指标
    #       返回: pe, pb, ps, pcf, market_cap, circulating_cap
    #   - /api/v1/rank/hot: 热门股票排行
    #       返回: code, name, price, change_pct, volume, amount
    #   - /api/v1/dragon_tiger/daily: 龙虎榜
    #       参数: date, market(沪深/上海/深圳)
    #       返回: code, name, close_price, change_pct, lhb_reason, buy_total, sell_total
    #       包含: 营业部买卖明细
    #   - /api/v1/industry/stock/{code}: 个股行业信息
    #       返回: industry, industry_code
    #
    # 优势: 财务数据覆盖最广，A股特色数据(龙虎榜、大宗交易等)
    # 劣势: 部分接口依赖爬虫，可能变更，频率限制较严(~20次/分钟)
    # --------------------------------------------------------
    DataSource.AKSHARE_API: DataSourceCapability(
        name="akshare-api",
        display_name="AkShare",
        supported_types=(DataType.FINANCE, DataType.VALUATION, DataType.RANKING, DataType.DRAGON_TIGER, DataType.INDUSTRY),
        latency_ms=(300, 2000),
        reliability=0.90,
        requires_network=True,
        rate_limit=20,
        notes="财务数据覆盖最广，A股特色数据(龙虎榜等)；缺点：部分接口依赖爬虫"
    ),
    
    # --------------------------------------------------------
    # PYWENCAI - 同花顺问财
    # --------------------------------------------------------
    # 协议: HTTP REST API (自建云端服务封装)
    # 数据来源: 同花顺问财 (自然语言查询)
    #
    # 支持的接口:
    #   - /api/v1/query: 自然语言查询
    #       参数: q(查询语句), perpage(每页数量)
    #       示例查询:
    #         - "今日涨停" → 返回今日涨停股票列表
    #         - "连续3日涨停" → 返回连板股
    #         - "市值低于50亿的科技股" → 条件筛选
    #       返回: 动态列 (根据查询内容变化)
    #
    # 优势: 唯一支持中文自然语言查询，强大的条件筛选能力
    # 劣势: 反爬严格(验证码)，失败率高(~30%)，频率限制严(~10次/分钟)
    # --------------------------------------------------------
    DataSource.PYWENCAI_API: DataSourceCapability(
        name="pywencai-api",
        display_name="同花顺问财",
        supported_types=(DataType.SECTOR,),
        latency_ms=(1000, 5000),
        reliability=0.70,
        requires_network=True,
        rate_limit=10,
        notes="唯一支持自然语言查询(如'今日涨停')；缺点：反爬严格，失败率高"
    ),
}


# ============================================================
# 降级链配置
# 当主数据源失败时，按顺序尝试备选数据源
# ============================================================

FALLBACK_CHAINS: Dict[DataType, List[DataSource]] = {
    DataType.QUOTES: [DataSource.MOOTDX, DataSource.EASYQUOTATION],
    DataType.TICK: [DataSource.MOOTDX],  # 无备选
    DataType.HISTORY: [DataSource.BAOSTOCK_API, DataSource.MOOTDX],
    DataType.RANKING: [DataSource.AKSHARE_API],  # 无备选
    DataType.SECTOR: [DataSource.PYWENCAI_API],  # 无备选
    DataType.FINANCE: [DataSource.AKSHARE_API, DataSource.BAOSTOCK_API],
    DataType.VALUATION: [DataSource.AKSHARE_API],  # 无备选
    DataType.INDEX: [DataSource.BAOSTOCK_API],  # 无备选
    DataType.INDUSTRY: [DataSource.BAOSTOCK_API, DataSource.AKSHARE_API],
    DataType.DRAGON_TIGER: [DataSource.AKSHARE_API],  # 无备选
    
    # Mootdx 扩展 (无备选，mootdx 是唯一本地源)
    DataType.STOCK_LIST: [DataSource.MOOTDX],
    DataType.FINANCE_INFO: [DataSource.MOOTDX],
    DataType.XDXR: [DataSource.MOOTDX],
    DataType.INDEX_BARS: [DataSource.MOOTDX],
}

