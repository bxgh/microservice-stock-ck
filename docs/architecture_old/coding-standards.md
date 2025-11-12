# 编码规范文档

## 📋 文档信息

- **文档版本**: v1.0
- **创建日期**: 2025-11-05
- **作者**: Winston (Architect Agent)
- **适用范围**: 股票数据分析系统
- **代码风格**: Black + isort + mypy
- **最后更新**: 2025-11-05

---

## 🎯 概述

本文档定义了股票数据分析系统的编码规范，旨在确保代码质量、可读性和一致性。遵循这些规范将提高团队协作效率，降低维护成本，并减少潜在的错误。

---

## 🔧 开发环境配置

### 必需工具

```bash
# 安装开发依赖
pip install black isort flake8 mypy pytest pytest-cov pre-commit

# 安装pre-commit钩子
pre-commit install
```

### IDE配置

#### VSCode配置 (`.vscode/settings.json`)

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests"
  ]
}
```

#### PyCharm配置

1. **代码风格**: 设置 → 编辑器 → 代码风格 → Python → 导入 Black
2. **导入优化**: 设置 → 编辑器 → 代码风格 → Python → 优化导入
3. **类型检查**: 设置 → 工具 → MyPy

### Pre-commit配置 (`.pre-commit-config.yaml`)

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

---

## 🐍 Python编码规范

### 1. 基础规范

#### 1.1 缩进和空格

```python
# ✅ 正确：使用4个空格缩进
def calculate_volume_distribution(tick_data: List[Dict]) -> Dict[str, float]:
    volume_by_price = {}

    for trade in tick_data:
        price = trade['price']
        volume = trade['volume']

        if price in volume_by_price:
            volume_by_price[price] += volume
        else:
            volume_by_price[price] = volume

    return volume_by_price

# ❌ 错误：使用Tab或混用空格和Tab
def calculate_volume_distribution(tick_data):
	volume_by_price = {}
	for trade in tick_data:
		price = trade['price']   # Tab缩进
		volume = trade['volume']
```

#### 1.2 行长度

```python
# ✅ 正确：行长度不超过88字符
def analyze_tick_data(
    symbol: str,
    date: str,
    market: MarketType = MarketType.SZ
) -> AnalysisResult:
    """分析分笔数据

    Args:
        symbol: 股票代码
        date: 交易日期
        market: 市场类型

    Returns:
        分析结果
    """
    pass

# ❌ 错误：行长度超过88字符
def analyze_tick_data_for_shanghai_market_with_specific_date_and_volume_analysis(symbol: str, date: str) -> AnalysisResult:
    pass
```

#### 1.3 空行使用

```python
# ✅ 正确：合理的空行使用
class StockDataAnalyzer:
    """股票数据分析器"""

    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)


    def analyze_volume(self, tick_data: List[Dict]) -> VolumeAnalysis:
        """分析成交量分布"""
        # 处理数据
        processed_data = self._preprocess_data(tick_data)

        # 计算分布
        distribution = self._calculate_distribution(processed_data)

        return distribution


    def _preprocess_data(self, data: List[Dict]) -> List[Dict]:
        """预处理数据"""
        return [self._validate_trade(trade) for trade in data]

# ❌ 错误：过多的空行或缺少必要的空行
class StockDataAnalyzer:
    """股票数据分析器"""




    def __init__(self, config: AnalyzerConfig):


        self.config = config
        self.logger = logging.getLogger(__name__)
    def analyze_volume(self, tick_data: List[Dict]) -> VolumeAnalysis:
        # 缺少类方法间的空行
        pass
```

### 2. 命名规范

#### 2.1 变量和函数命名

```python
# ✅ 正确：使用snake_case
def get_real_time_quotes(symbols: List[str]) -> Dict[str, QuoteData]:
    """获取实时行情数据"""
    stock_symbols = symbols  # 变量名要有意义
    cache_key = f"quotes:{','.join(stock_symbols)}"

    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    fresh_data = fetch_from_data_source(stock_symbols)
    cache.set(cache_key, fresh_data, ttl=60)

    return fresh_data

# ❌ 错误：使用驼峰命名或无意义的名称
def getRealTimeQuotes(symbolList):  # 驼峰命名
    data = cache.get(k)  # 无意义的变量名
    return data
```

#### 2.2 类命名

```python
# ✅ 正确：使用PascalCase
class VolumeDistributionAnalyzer:
    """成交量分布分析器"""

    def __init__(self, config: AnalyzerConfig):
        self.config = config

class TickDataProcessor:
    """分笔数据处理器"""
    pass

# ❌ 错误：使用snake_case或缩写
class volume_analyzer:  # 小写开头
    pass

class VDA:  # 不清晰的缩写
    pass
```

#### 2.3 常量命名

```python
# ✅ 正确：使用全大写加下划线
DEFAULT_CACHE_TTL = 300  # 默认缓存TTL(秒)
MAX_RETRY_ATTEMPTS = 3   # 最大重试次数
API_BASE_URL = "https://api.example.com"  # API基础URL

class MarketType(Enum):
    SHANGHAI = "SH"  # 上海证券交易所
    SHENZHEN = "SZ"   # 深圳证券交易所

# ❌ 错误：使用小写或驼峰命名
default_cache_ttl = 300  # 常量应该大写
maxRetryAttempts = 3     # 常量应该大写
```

#### 2.4 私有成员命名

```python
# ✅ 正确：使用单下划线前缀
class DataProcessor:
    def __init__(self):
        self._cache = {}  # 私有缓存
        self._logger = logging.getLogger(__name__)

    def _validate_data(self, data: Dict) -> bool:
        """验证数据(私有方法)"""
        return 'price' in data and 'volume' in data

    def _calculate_vwap(self, trades: List[Dict]) -> float:
        """计算成交量加权平均价(私有方法)"""
        total_value = sum(trade['price'] * trade['volume'] for trade in trades)
        total_volume = sum(trade['volume'] for trade in trades)
        return total_value / total_volume if total_volume > 0 else 0.0

# ✅ 特殊情况：双下划线用于名称修饰
class BaseConfig:
    def __init__(self):
        self.__secret_key = "secret"  # 名称修饰，外部无法直接访问

    def get_key(self) -> str:
        return self.__secret_key
```

### 3. 类型注解

#### 3.1 基本类型注解

```python
# ✅ 正确：完整的类型注解
from typing import List, Dict, Optional, Union
from decimal import Decimal
from datetime import datetime, date

def process_quote_data(
    symbols: List[str],
    start_date: date,
    end_date: Optional[date] = None
) -> Dict[str, Union[QuoteData, None]]:
    """处理行情数据

    Args:
        symbols: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期，可选

    Returns:
        股票代码到行情数据的映射
    """
    results = {}
    for symbol in symbols:
        try:
            quote_data = fetch_quote_data(symbol, start_date, end_date)
            results[symbol] = quote_data
        except Exception as e:
            logger.error(f"获取{symbol}数据失败: {e}")
            results[symbol] = None

    return results

# ❌ 错误：缺少类型注解或注解不准确
def process_quote_data(symbols, start_date, end_date=None):  # 缺少类型注解
    results = {}
    return results
```

#### 3.2 复杂类型注解

```python
# ✅ 正确：使用TypeVar和Generic
from typing import TypeVar, Generic, Protocol

T = TypeVar('T')

class Cache(Protocol):
    """缓存协议"""
    async def get(self, key: str) -> Optional[T]:
        ...

    async def set(self, key: str, value: T, ttl: int) -> None:
        ...

class DataRepository(Generic[T]):
    """通用数据仓储"""

    def __init__(self, cache: Cache[T]):
        self._cache = cache

    async def get_data(self, key: str) -> Optional[T]:
        return await self._cache.get(key)

    async def save_data(self, key: str, data: T, ttl: int = 300) -> None:
        await self._cache.set(key, data, ttl)

# 使用示例
quote_repository = DataRepository[QuoteData](redis_cache)
tick_repository = DataRepository[TickData](redis_cache)
```

#### 3.3 返回类型注解

```python
# ✅ 正确：明确的返回类型注解
from typing import Tuple, Literal

def analyze_market_sentiment(
    tick_data: List[Dict]
) -> Tuple[Dict[str, float], Literal["bullish", "bearish", "neutral"]]:
    """分析市场情绪

    Returns:
        元组：(情绪指标, 情绪标签)
    """
    # 计算情绪指标
    buy_ratio = calculate_buy_ratio(tick_data)
    volume_trend = calculate_volume_trend(tick_data)

    sentiment_score = (buy_ratio * 0.6) + (volume_trend * 0.4)

    # 确定情绪标签
    if sentiment_score > 0.6:
        sentiment = "bullish"
    elif sentiment_score < 0.4:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    return {"score": sentiment_score, "buy_ratio": buy_ratio}, sentiment

# ❌ 错误：返回类型不明确或错误
def analyze_market_sentiment(tick_data):
    # 应该返回元组，但类型注解错误
    return {"score": 0.5}, "bullish"
```

### 4. 函数和方法规范

#### 4.1 函数定义

```python
# ✅ 正确：结构良好的函数定义
def fetch_tick_data(
    symbol: str,
    date: str,
    market: MarketType = MarketType.SZ,
    timeout: int = 30,
    retry_attempts: int = 3
) -> Optional[TickData]:
    """获取分笔数据

    Args:
        symbol: 股票代码，如 '000001'
        date: 交易日期，格式 'YYYYMMDD'
        market: 市场类型，默认深圳
        timeout: 请求超时时间(秒)，默认30秒
        retry_attempts: 重试次数，默认3次

    Returns:
        分笔数据，获取失败返回None

    Raises:
        ValueError: 当股票代码或日期格式无效时
        DataSourceError: 当数据源不可用时
        TimeoutError: 当请求超时时

    Example:
        >>> data = fetch_tick_data('000001', '20251105')
        >>> if data:
        ...     print(f"获取到{len(data.trades)}条交易记录")
    """
    # 参数验证
    if not validate_symbol(symbol):
        raise ValueError(f"无效的股票代码: {symbol}")

    if not validate_date(date):
        raise ValueError(f"无效的日期格式: {date}")

    # 重试逻辑
    for attempt in range(retry_attempts):
        try:
            data = await _fetch_from_source(symbol, date, market, timeout)
            if data and len(data.trades) > 0:
                return data
        except TimeoutError:
            if attempt == retry_attempts - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # 指数退避

    return None

# ❌ 错误：缺少文档或参数验证
def fetch_tick_data(symbol, date, market='SZ', timeout=30, retry_attempts=3):
    # 缺少参数验证和文档字符串
    return await _fetch_from_source(symbol, date, market, timeout)
```

#### 4.2 类方法定义

```python
# ✅ 正确：类方法规范
class TechnicalIndicator:
    """技术指标计算器"""

    def __init__(self, config: IndicatorConfig):
        self.config = config
        self._logger = logging.getLogger(self.__class__.__name__)

    def calculate_ma(
        self,
        prices: List[float],
        period: int,
        ma_type: str = "sma"
    ) -> List[float]:
        """计算移动平均线

        Args:
            prices: 价格序列
            period: 周期
            ma_type: 移动平均类型 (sma/ema)

        Returns:
            移动平均线序列

        Raises:
            ValueError: 当period <= 0 或 prices为空时
        """
        if period <= 0:
            raise ValueError("周期必须大于0")

        if not prices:
            raise ValueError("价格序列不能为空")

        if len(prices) < period:
            self._logger.warning(f"价格序列长度({len(prices)})小于周期({period})")
            return []

        if ma_type.lower() == "sma":
            return self._calculate_sma(prices, period)
        elif ma_type.lower() == "ema":
            return self._calculate_ema(prices, period)
        else:
            raise ValueError(f"不支持的移动平均类型: {ma_type}")

    def _calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """计算简单移动平均线(私有方法)"""
        return [
            sum(prices[i:i+period]) / period
            for i in range(len(prices) - period + 1)
        ]

    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """计算指数移动平均线(私有方法)"""
        multiplier = 2 / (period + 1)
        ema = [prices[0]]

        for price in prices[1:]:
            ema.append((price * multiplier) + (ema[-1] * (1 - multiplier)))

        return ema

    @classmethod
    def create_default(cls) -> 'TechnicalIndicator':
        """创建默认配置的指标计算器

        Returns:
            TechnicalIndicator实例
        """
        config = IndicatorConfig(
            default_period=20,
            smoothing_factor=2.0
        )
        return cls(config)

    @staticmethod
    def validate_price_sequence(prices: List[float]) -> bool:
        """验证价格序列有效性

        Args:
            prices: 价格序列

        Returns:
            是否有效
        """
        if not prices:
            return False

        return all(price > 0 for price in prices)
```

### 5. 异常处理规范

#### 5.1 异常定义

```python
# ✅ 正确：自定义异常类定义
class StockDataError(Exception):
    """股票数据基础异常"""

    def __init__(self, message: str, error_code: str = None, context: Dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = datetime.now()

class DataSourceError(StockDataError):
    """数据源异常"""
    pass

class ValidationError(StockDataError):
    """数据验证异常"""
    pass

class CacheError(StockDataError):
    """缓存异常"""
    pass

# ✅ 正确：使用自定义异常
def validate_quote_data(data: Dict) -> QuoteData:
    """验证行情数据"""
    required_fields = ['symbol', 'price', 'volume', 'timestamp']

    for field in required_fields:
        if field not in data:
            raise ValidationError(
                f"缺少必需字段: {field}",
                error_code="MISSING_FIELD",
                context={"field": field, "data": data}
            )

    if data['price'] <= 0:
        raise ValidationError(
            f"价格必须大于0: {data['price']}",
            error_code="INVALID_PRICE",
            context={"price": data['price']}
        )

    return QuoteData.from_dict(data)

# ❌ 错误：直接使用通用异常
def validate_quote_data(data: Dict):
    if 'price' not in data:
        raise Exception("缺少价格字段")  # 应该使用具体的异常类型
```

#### 5.2 异常处理

```python
# ✅ 正确：结构化的异常处理
async def fetch_and_process_data(symbols: List[str]) -> Dict[str, QuoteData]:
    """获取并处理数据"""
    results = {}

    for symbol in symbols:
        try:
            # 尝试获取数据
            raw_data = await fetch_from_data_source(symbol)

            # 验证数据
            validated_data = validate_quote_data(raw_data)

            # 处理数据
            processed_data = process_quote_data(validated_data)
            results[symbol] = processed_data

        except DataSourceError as e:
            logger.error(f"数据源错误 - {symbol}: {e}")
            results[symbol] = None

        except ValidationError as e:
            logger.warning(f"数据验证失败 - {symbol}: {e}")
            results[symbol] = None

        except Exception as e:
            logger.error(f"未知错误 - {symbol}: {e}", exc_info=True)
            results[symbol] = None

    return results

# ✅ 正确：使用finally进行资源清理
def process_large_dataset(file_path: str) -> AnalysisResult:
    """处理大型数据集"""
    file_handle = None

    try:
        file_handle = open(file_path, 'r', encoding='utf-8')
        data = json.load(file_handle)

        return analyze_data(data)

    except FileNotFoundError:
        raise DataSourceError(f"文件不存在: {file_path}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"JSON格式错误: {e}")
    finally:
        if file_handle:
            file_handle.close()

# ❌ 错误：过于宽泛的异常捕获
async def fetch_and_process_data(symbols: List[str]):
    results = {}
    for symbol in symbols:
        try:
            data = await fetch_from_data_source(symbol)
            results[symbol] = data
        except Exception:  # 过于宽泛，掩盖了具体错误
            logger.error(f"处理{symbol}失败")
            results[symbol] = None
    return results
```

### 6. 日志记录规范

#### 6.1 日志配置和使用

```python
# ✅ 正确：结构化日志记录
import structlog

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

class DataAcquisitionService:
    """数据获取服务"""

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    async def get_quotes(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """获取行情数据"""
        self.logger.info("开始获取行情数据", symbols=symbols, count=len(symbols))

        results = {}
        for symbol in symbols:
            start_time = time.time()

            try:
                data = await self._fetch_single_quote(symbol)
                results[symbol] = data

                duration = time.time() - start_time
                self.logger.info(
                    "成功获取行情数据",
                    symbol=symbol,
                    price=data.price,
                    duration=duration
                )

            except Exception as e:
                duration = time.time() - start_time
                self.logger.error(
                    "获取行情数据失败",
                    symbol=symbol,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration=duration,
                    exc_info=True
                )
                results[symbol] = None

        success_count = sum(1 for v in results.values() if v is not None)
        self.logger.info(
            "批量获取完成",
            total=len(symbols),
            success=success_count,
            failed=len(symbols) - success_count
        )

        return results

# ❌ 错误：日志信息不够详细
async def get_quotes(symbols):
    results = {}
    for symbol in symbols:
        try:
            data = await fetch_quote(symbol)
            results[symbol] = data
            print(f"获取{symbol}成功")  # 使用print而不是logging
        except Exception as e:
            print(f"获取{symbol}失败: {e}")  # 缺少上下文信息
    return results
```

#### 6.2 日志级别使用

```python
# ✅ 正确：合理使用日志级别
class DataProcessor:
    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    def process_data(self, data: List[Dict]) -> ProcessingResult:
        # DEBUG: 详细的调试信息
        self.logger.debug("开始处理数据", data_count=len(data))

        if not data:
            self.logger.warning("接收到空数据")
            return ProcessingResult.empty()

        try:
            # INFO: 重要的业务流程信息
            self.logger.info("数据预处理开始", data_type=type(data).__name__)
            processed_data = self._preprocess(data)

            # INFO: 关键步骤完成
            self.logger.info(
                "数据预处理完成",
                input_count=len(data),
                output_count=len(processed_data)
            )

            result = self._analyze(processed_data)

            # INFO: 业务流程完成
            self.logger.info(
                "数据处理完成",
                result_type=type(result).__name__,
                processing_time=result.processing_time
            )

            return result

        except Exception as e:
            # ERROR: 错误信息，包含详细上下文
            self.logger.error(
                "数据处理失败",
                error=str(e),
                error_type=type(e).__name__,
                data_preview=data[:5] if data else [],
                exc_info=True
            )
            raise

# ❌ 错误：日志级别使用不当
def process_data(data):
    # 不应该用ERROR记录正常流程
    logger.error(f"开始处理{len(data)}条数据")

    try:
        result = analyze(data)
        # 成功信息应该用INFO级别
        logger.error(f"处理成功: {result}")
        return result
    except Exception as e:
        # 错误信息缺少上下文
        logger.error(f"处理失败")
        raise
```

### 7. 文档字符串规范

#### 7.1 模块文档字符串

```python
# ✅ 正确：完整的模块文档字符串
"""
股票数据分析核心模块

本模块提供股票数据获取、处理和分析的核心功能。支持实时行情、历史数据、
分笔数据的获取，以及各种技术指标的计算。

主要功能:
    - 实时行情数据获取
    - 历史K线数据查询
    - 分笔成交数据分析
    - 技术指标计算
    - 市场情绪分析

使用示例:
    >>> from src.domain.services.data_acquisition import DataAcquisitionService
    >>> service = DataAcquisitionService()
    >>> quotes = await service.get_quotes(['000001', '600036'])
    >>> print(f"获取到{len(quotes)}只股票的行情数据")

注意事项:
    - 实时数据仅在交易时间内可用
    - 分笔数据量较大，建议分批处理
    - 使用前请确保网络连接稳定

作者: Winston (Architect Agent)
版本: 1.0.0
"""

# ❌ 错误：模块文档过于简单
"""股票数据处理模块"""
```

#### 7.2 类文档字符串

```python
# ✅ 正确：详细的类文档字符串
class VolumeDistributionAnalyzer:
    """成交量分布分析器

    用于分析股票分笔数据中的成交量分布特征，识别支撑位和阻力位，
    分析买卖力量对比，检测异常交易活动。

    主要功能:
        - 计算成交量分布直方图
        - 识别成交密集区域
        - 分析买卖力量对比
        - 检测大单交易活动

    使用示例:
        >>> analyzer = VolumeDistributionAnalyzer()
        >>> tick_data = fetch_tick_data('000001', '20251105')
        >>> result = analyzer.analyze(tick_data)
        >>> print(f"成交量分布: {result.distribution}")

    属性:
        min_price_interval (float): 最小价格间隔，默认0.01元
        min_volume_threshold (int): 最小成交量阈值，默认100股

    注意事项:
        - 输入数据必须是按时间排序的分笔数据
        - 价格和成交量必须为正数
        - 建议数据量不少于100条记录

    作者: Winston (Architect Agent)
    版本: 1.0.0
    """

    def __init__(self, min_price_interval: float = 0.01, min_volume_threshold: int = 100):
        """初始化分析器

        Args:
            min_price_interval: 价格分组的最小间隔
            min_volume_threshold: 成交量的最小阈值
        """
        self.min_price_interval = min_price_interval
        self.min_volume_threshold = min_volume_threshold
        self._logger = logging.getLogger(self.__class__.__name__)

# ❌ 错误：类文档过于简单
class VolumeAnalyzer:
    """成交量分析器"""
    pass
```

#### 7.3 函数文档字符串

```python
# ✅ 正确：完整的函数文档字符串
def calculate_vwap(
    tick_data: List[Dict[str, Union[float, int, str]]],
    price_precision: int = 2
) -> float:
    """计算成交量加权平均价格(VWAP)

    VWAP (Volume Weighted Average Price) 是成交量加权平均价，
    是衡量交易平均成本的重要指标。

    计算公式:
        VWAP = Σ(价格 × 成交量) / Σ(成交量)

    Args:
        tick_data: 分笔数据列表，每个元素包含:
            - price (float): 成交价格
            - volume (int): 成交数量
            - timestamp (str): 时间戳
        price_precision: 价格精度，小数位数，默认2位

    Returns:
        float: VWAP价格，如果无有效数据返回0.0

    Raises:
        ValueError: 当tick_data为空或数据格式不正确时

    Example:
        >>> data = [
        ...     {'price': 10.50, 'volume': 1000, 'timestamp': '09:30:00'},
        ...     {'price': 10.51, 'volume': 500, 'timestamp': '09:30:01'}
        ... ]
        >>> vwap = calculate_vwap(data)
        >>> print(f"VWAP: {vwap:.2f}")
        VWAP: 10.50

    Note:
        - 过滤掉价格或成交量为非正数的数据
        - 价格精度会影响返回值的小数位数
        - 适用于日内VWAP计算，日间VWAP需要另外处理

    See Also:
        calculate_twap: 时间加权平均价格
        calculate_vwap_profile: VWAP分布曲线
    """
    if not tick_data:
        raise ValueError("分笔数据不能为空")

    total_value = 0.0
    total_volume = 0

    for trade in tick_data:
        try:
            price = float(trade['price'])
            volume = int(trade['volume'])

            if price <= 0 or volume <= 0:
                continue

            total_value += price * volume
            total_volume += volume

        except (KeyError, ValueError, TypeError) as e:
            continue

    if total_volume == 0:
        return 0.0

    vwap = total_value / total_volume
    return round(vwap, price_precision)

# ❌ 错误：函数文档不完整
def calculate_vwap(tick_data, price_precision=2):
    """计算VWAP"""
    total_value = 0
    total_volume = 0
    for trade in tick_data:
        total_value += trade['price'] * trade['volume']
        total_volume += trade['volume']
    return total_value / total_volume if total_volume > 0 else 0
```

### 8. 代码注释规范

#### 8.1 注释原则

```python
# ✅ 正确：有用且简洁的注释
class StockDataAnalyzer:
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self._cache = {}  # 内存缓存，减少重复计算

        # 初始化分析器组件
        self._volume_analyzer = VolumeAnalyzer(config.volume)
        self._price_analyzer = PriceAnalyzer(config.price)

        self._logger = logging.getLogger(__name__)

    def analyze_tick_data(self, tick_data: List[Dict]) -> AnalysisResult:
        """分析分笔数据"""
        # 数据预处理：过滤无效数据
        valid_trades = [
            trade for trade in tick_data
            if trade.get('price', 0) > 0 and trade.get('volume', 0) > 0
        ]

        if not valid_trades:
            return AnalysisResult.empty()

        # 并行计算各种指标，提高效率
        volume_analysis = self._volume_analyzer.analyze(valid_trades)
        price_analysis = self._price_analyzer.analyze(valid_trades)

        # 综合分析结果
        return AnalysisResult.combine(volume_analysis, price_analysis)

# ❌ 错误：无用的注释或注释过多
class StockDataAnalyzer:
    def __init__(self, config):
        self.config = config  # 设置配置
        self._cache = {}  # 创建一个空的字典作为缓存

        # 创建成交量分析器
        self._volume_analyzer = VolumeAnalyzer(config.volume)
        # 创建价格分析器
        self._price_analyzer = PriceAnalyzer(config.price)

        # 获取logger
        self._logger = logging.getLogger(__name__)

    def analyze_tick_data(self, tick_data):
        # 开始分析分笔数据
        valid_trades = []  # 创建一个空列表
        for trade in tick_data:  # 遍历每个交易
            # 检查价格是否大于0
            if trade.get('price', 0) > 0:
                # 检查成交量是否大于0
                if trade.get('volume', 0) > 0:
                    # 添加到有效交易列表
                    valid_trades.append(trade)
```

#### 8.2 TODO和FIXME注释

```python
# ✅ 正确：标准化的TODO和FIXME注释
class DataProcessor:
    def process_data(self, data: List[Dict]) -> ProcessingResult:
        # TODO: 实现数据去重逻辑 (作者: 张三, 日期: 2025-11-12)
        # 目前可能存在重复数据，需要根据时间戳去重

        # FIXME: 这里的时间处理逻辑有bug，时区处理不正确 (作者: 李四, 日期: 2025-11-05)
        processed_timestamps = [
            datetime.strptime(trade['time'], '%H:%M:%S')
            for trade in data
        ]

        # NOTE: 性能优化点：可以考虑使用向量化操作提高处理速度
        # 当前实现在大数据量时可能较慢
        return self._analyze_data(processed_timestamps)

# ❌ 错误：不规范的TODO注释
class DataProcessor:
    def process_data(self, data):
        # todo: 这里需要改
        processed_data = some_processing(data)

        # fixme: 有bug
        return processed_data
```

### 9. 代码组织规范

#### 9.1 导入语句组织

```python
# ✅ 正确：按标准顺序组织导入
# 标准库导入
import os
import sys
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Union
from pathlib import Path

# 第三方库导入
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import redis
import structlog

# 本地模块导入
from src.core.config.manager import ConfigManager
from src.core.exceptions.base import StockDataError
from src.domain.models.quote import QuoteData, TickData
from src.application.services.data_acquisition import DataAcquisitionService
from src.infrastructure.adapters.data_sources.mootdx_adapter import MootdxAdapter

# 相对导入(仅在同一包内使用)
from .utils import validate_symbol
from .constants import DEFAULT_TIMEOUT

# ❌ 错误：导入顺序混乱或使用通配符导入
import os
from fastapi import *
import sys
from src.domain.models import *
from src.core.config import *
import pandas as pd
from datetime import datetime
```

#### 9.2 模块组织

```python
# ✅ 正确：模块内容按逻辑组织
"""股票数据获取模块"""

# 1. 常量定义
__all__ = ['DataAcquisitionService', 'BatchProcessor']

DEFAULT_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
CACHE_TTL = 60

# 2. 导入语句
import asyncio
import logging
from typing import List, Dict, Optional

# 3. 类和函数定义
class DataAcquisitionService:
    """数据获取服务"""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self._logger = logging.getLogger(__name__)

class BatchProcessor:
    """批量处理器"""
    pass

# 4. 辅助函数
def _validate_symbols(symbols: List[str]) -> List[str]:
    """验证股票代码"""
    return [s for s in symbols if validate_symbol(s)]

# 5. 模块初始化代码(如果需要)
def _setup_logging():
    """设置日志"""
    logging.basicConfig(level=logging.INFO)

_setup_logging()

# ❌ 错误：模块内容组织混乱
"""股票数据获取模块"""

from typing import List
import asyncio

class DataAcquisitionService:
    pass

DEFAULT_TIMEOUT = 30  # 常量定义应该在模块开头

def helper_function():
    pass  # 辅助函数应该在类定义之后

class BatchProcessor:
    pass

import logging  # 导入语句应该集中在模块开头
```

### 10. 性能相关规范

#### 10.1 异步编程规范

```python
# ✅ 正确：异步编程最佳实践
import asyncio
from typing import List, Optional

class AsyncDataFetcher:
    """异步数据获取器"""

    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._session:
            await self._session.close()

    async def fetch_batch_data(self, symbols: List[str]) -> Dict[str, Optional[QuoteData]]:
        """批量获取数据"""
        # 使用信号量控制并发数
        tasks = [
            self._fetch_single_data(symbol)
            for symbol in symbols
        ]

        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        return {
            symbol: result if not isinstance(result, Exception) else None
            for symbol, result in zip(symbols, results)
        }

    async def _fetch_single_data(self, symbol: str) -> QuoteData:
        """获取单个股票数据"""
        async with self.semaphore:  # 控制并发数
            try:
                # 实际的数据获取逻辑
                async with self._session.get(
                    f"/api/quotes/{symbol}",
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    data = await response.json()
                    return QuoteData.from_dict(data)

            except asyncio.TimeoutError:
                self._logger.warning(f"获取{symbol}数据超时")
                raise
            except Exception as e:
                self._logger.error(f"获取{symbol}数据失败: {e}")
                raise

# 使用示例
async def main():
    symbols = ['000001', '000002', '600036', '600519']

    async with AsyncDataFetcher(max_concurrent=5) as fetcher:
        results = await fetcher.fetch_batch_data(symbols)

    for symbol, data in results.items():
        if data:
            print(f"{symbol}: {data.price}")
        else:
            print(f"{symbol}: 获取失败")

# ❌ 错误：不当的异步编程方式
class BadAsyncFetcher:
    async def fetch_data(self, symbols):
        results = {}
        for symbol in symbols:  # 不应该串行执行
            data = await self._fetch_single(symbol)  # 没有并发控制
            results[symbol] = data
        return results

    async def _fetch_single(self, symbol):
        # 缺少错误处理和超时控制
        response = await self._session.get(f"/api/quotes/{symbol}")
        data = await response.json()
        return data
```

#### 10.2 内存和性能优化

```python
# ✅ 正确：内存高效的数据处理
import gc
from typing import Iterator, Generator

class MemoryEfficientProcessor:
    """内存高效的数据处理器"""

    def process_large_dataset(self, file_path: str) -> Iterator[AnalysisResult]:
        """处理大型数据集，使用生成器避免内存溢出"""

        def chunk_generator(chunk_size: int = 1000) -> Generator[List[Dict], None, None]:
            """分块读取数据的生成器"""
            with open(file_path, 'r', encoding='utf-8') as file:
                chunk = []
                for line in file:
                    try:
                        record = json.loads(line.strip())
                        chunk.append(record)

                        if len(chunk) >= chunk_size:
                            yield chunk
                            chunk = []  # 清空当前块

                    except json.JSONDecodeError:
                        continue

                if chunk:  # 处理最后一块
                    yield chunk

        # 分块处理数据
        for chunk in chunk_generator():
            # 处理当前块
            result = self._process_chunk(chunk)
            yield result

            # 手动触发垃圾回收
            del chunk
            gc.collect()

    def _process_chunk(self, chunk: List[Dict]) -> AnalysisResult:
        """处理数据块"""
        # 使用pandas进行向量化计算
        df = pd.DataFrame(chunk)

        # 向量化操作比循环快很多
        df['vwap'] = (df['price'] * df['volume']).cumsum() / df['volume'].cumsum()
        df['price_change'] = df['price'].pct_change()

        return AnalysisResult.from_dataframe(df)

# ✅ 正确：使用缓存优化性能
from functools import lru_cache
import hashlib

class CachedAnalyzer:
    """带缓存的分析器"""

    def __init__(self, cache_size: int = 128):
        self.cache_size = cache_size

    @lru_cache(maxsize=128)
    def calculate_indicators(self, data_hash: str, data_tuple: tuple) -> Dict[str, float]:
        """计算技术指标，带缓存"""
        # 将数据转换为元组以支持缓存
        prices = [item[0] for item in data_tuple]
        volumes = [item[1] for item in data_tuple]

        # 计算指标
        indicators = {
            'sma_20': self._calculate_sma(prices, 20),
            'ema_12': self._calculate_ema(prices, 12),
            'volume_ratio': self._calculate_volume_ratio(volumes),
        }

        return indicators

    def analyze_with_cache(self, tick_data: List[Dict]) -> Dict[str, float]:
        """带缓存的分析"""
        # 创建数据哈希作为缓存键
        data_str = json.dumps(tick_data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()

        # 转换为可哈希的元组
        data_tuple = tuple(
            (item['price'], item['volume'])
            for item in tick_data
        )

        return self.calculate_indicators(data_hash, data_tuple)

# ❌ 错误：内存使用不当
class InefficientProcessor:
    def process_large_dataset(self, file_path: str):
        # 一次性读取所有数据，可能导致内存溢出
        with open(file_path, 'r') as file:
            data = [json.loads(line) for line in file]  # 大文件会占用大量内存

        # 嵌套循环，性能很差
        results = []
        for i, record1 in enumerate(data):
            for j, record2 in enumerate(data):
                if i != j:
                    # 一些计算
                    result = self._calculate(record1, record2)
                    results.append(result)

        return results
```

---

## 🔍 代码审查检查清单

### 提交代码前的检查项

- [ ] **代码格式化**: 运行 `black .` 格式化代码
- [ ] **导入排序**: 运行 `isort .` 排序导入
- [ ] **类型检查**: 运行 `mypy src/` 检查类型
- [ ] **代码质量**: 运行 `flake8 src/` 检查代码质量
- [ ] **测试覆盖**: 运行 `pytest --cov=src tests/` 检查测试覆盖率
- [ ] **文档字符串**: 所有公共函数和类都有完整的docstring
- [ ] **类型注解**: 所有函数都有类型注解
- [ ] **异常处理**: 合理处理各种异常情况
- [ ] **日志记录**: 关键操作有适当的日志记录
- [ ] **性能考虑**: 避免明显的性能问题

### 代码审查重点关注

1. **可读性**: 代码是否易于理解和维护
2. **正确性**: 逻辑是否正确，边界条件是否处理
3. **性能**: 是否存在明显的性能问题
4. **安全性**: 是否存在安全漏洞
5. **测试**: 是否有足够的测试覆盖

---

## 📚 参考资源

### 官方文档

- [PEP 8 -- Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 484 -- Type Hints](https://peps.python.org/pep-0484/)
- [PEP 525 -- Asynchronous Generators](https://peps.python.org/pep-0525/)
- [Python Documentation](https://docs.python.org/3/)

### 工具文档

- [Black: The uncompromising code formatter](https://black.readthedocs.io/)
- [isort: Python import sorter](https://isort.readthedocs.io/)
- [flake8: Linting tool](https://flake8.pycqa.org/)
- [mypy: Static type checker](https://mypy.readthedocs.io/)
- [pytest: Testing framework](https://docs.pytest.org/)

### 最佳实践

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/best-practices/)
- [AsyncIO Best Practices](https://docs.python.org/3/library/asyncio-dev.html)

---

## 📝 文档维护

- **版本**: v1.0
- **创建日期**: 2025-11-05
- **作者**: Winston (Architect Agent)
- **审核人**: 技术团队
- **下次更新**: 2025-12-05
- **更新频率**: 季度评审

---

**注意事项**:
1. 本规范是强制性的，所有代码都必须遵循
2. 如有特殊情况需要偏离规范，必须经过技术负责人批准
3. 规范会根据项目发展和团队反馈定期更新
4. 新人入职时必须学习并通过编码规范考核