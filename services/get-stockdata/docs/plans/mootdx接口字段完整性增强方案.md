# 📊 mootdx接口字段完整性增强方案

## 🔍 **mootdx接口现状分析**

### **当前可用字段**
基于实际使用情况分析，mootdx接口提供以下核心字段：

```python
# 基础分笔数据字段 (当前已实现)
mootdx_base_fields = {
    'time': '时间',           # 格式: HH:MM:SS
    'price': '价格',         # 成交价格
    'volume': '成交量',       # 成交数量
    'amount': '成交额',       # 成交金额
    'direction': '买卖方向'   # 1=买, -1=卖, 0=中性
}

# 数据结构示例
mootdx_data_structure = [
    "09:30:00",  # 时间
    11.50,        # 价格
    1000,         # 成交量
    11500.0,      # 成交额
    1            # 方向 (1=买盘)
]
```

### **mootdx接口限制**
- **字段深度有限**：仅提供基础的5个字段
- **衍生信息缺失**：无市场深度、订单类型等信息
- **计算字段缺失**：无价格变动、技术指标等

## 🎯 **字段完整性增强策略**

### **策略一：基于mootdx的字段衍生计算** (优先级：1)

#### 1.1 实时衍生字段计算引擎
```python
class MootdxFieldEnhancer:
    def __init__(self):
        self.tick_history = []
        self.volume_history = []
        self.price_history = []
        self.direction_history = []

    def enhance_tick_data(self, raw_data: List[List]) -> List[Dict]:
        """
        增强mootdx原始数据，计算衍生字段
        """
        enhanced_data = []

        for i, tick in enumerate(raw_data):
            # 基础字段直接映射
            enhanced_tick = self._map_base_fields(tick)

            # 衍生字段计算
            enhanced_tick.update(self._calculate_derived_fields(tick, i))

            enhanced_data.append(enhanced_tick)

            # 更新历史数据
            self._update_history(enhanced_tick)

        return enhanced_data

    def _map_base_fields(self, tick: List) -> Dict[str, Any]:
        """映射基础字段到标准格式"""
        return {
            'time': self._parse_time(tick[0]),
            'price': float(tick[1]),
            'volume': int(tick[2]),
            'amount': float(tick[3]),
            'direction': self._convert_direction(tick[4]),
            'code': '',  # 需要从外部传入
            'date': '',  # 需要从外部传入
        }
```

#### 1.2 衍生字段计算规则
```python
def _calculate_derived_fields(self, tick: List, index: int) -> Dict[str, Any]:
    """计算所有衍生字段"""
    current_price = float(tick[1])
    current_volume = int(tick[2])
    current_direction = tick[4]

    # 1. 价格变动相关字段
    price_fields = self._calculate_price_fields(current_price, index)

    # 2. 成交量相关字段
    volume_fields = self._calculate_volume_fields(current_volume, index)

    # 3. 方向分析字段
    direction_fields = self._calculate_direction_fields(current_direction, index)

    # 4. 市场微观结构字段
    microstructure_fields = self._calculate_microstructure_fields(index)

    return {
        **price_fields,
        **volume_fields,
        **direction_fields,
        **microstructure_fields
    }

def _calculate_price_fields(self, current_price: float, index: int) -> Dict[str, Any]:
    """计算价格相关衍生字段"""
    fields = {}

    # 价格变动 (相对前一笔)
    if index > 0 and self.price_history:
        prev_price = self.price_history[-1]
        price_change = current_price - prev_price
        price_change_pct = (price_change / prev_price) * 100

        fields.update({
            'price_change': round(price_change, 4),
            'price_change_pct': round(price_change_pct, 2),
            'price_high': max(current_price, max(self.price_history)),
            'price_low': min(current_price, min(self.price_history))
        })
    else:
        fields.update({
            'price_change': 0.0,
            'price_change_pct': 0.0,
            'price_high': current_price,
            'price_low': current_price
        })

    return fields

def _calculate_volume_fields(self, current_volume: int, index: int) -> Dict[str, Any]:
    """计算成交量相关衍生字段"""
    fields = {}

    # 累计成交量
    cumulative_volume = sum(self.volume_history) + current_volume
    fields['cumulative_volume'] = cumulative_volume

    # 成交量占比 (相对累计)
    if cumulative_volume > 0:
        fields['volume_ratio'] = round(current_volume / cumulative_volume, 4)
    else:
        fields['volume_ratio'] = 1.0

    # 成交量移动平均 (最近N笔)
    if len(self.volume_history) >= 10:
        recent_volumes = self.volume_history[-9:] + [current_volume]
        fields['volume_ma_10'] = round(sum(recent_volumes) / 10, 0)
    else:
        fields['volume_ma_10'] = current_volume

    # 大单标识 (成交量超过平均值2倍)
    if len(self.volume_history) > 10:
        avg_volume = sum(self.volume_history[-20:]) / 20
        fields['is_large_order'] = current_volume > avg_volume * 2
    else:
        fields['is_large_order'] = False

    return fields

def _calculate_direction_fields(self, current_direction: int, index: int) -> Dict[str, Any]:
    """计算方向分析字段"""
    fields = {}

    # Tick方向判断
    if index > 0 and self.direction_history:
        prev_direction = self.direction_history[-1]
        if current_direction > prev_direction:
            fields['tick_direction'] = 'UP'      # 价格上涨
        elif current_direction < prev_direction:
            fields['tick_direction'] = 'DOWN'    # 价格下跌
        else:
            fields['tick_direction'] = 'FLAT'   # 价格不变
    else:
        fields['tick_direction'] = 'NEUTRAL'  # 第一笔

    # 买卖压力统计
    recent_directions = (self.direction_history[-20:] + [current_direction])
    buy_count = sum(1 for d in recent_directions if d > 0)
    sell_count = sum(1 for d in recent_directions if d < 0)

    total_trades = len([d for d in recent_directions if d != 0])
    if total_trades > 0:
        fields['buy_pressure'] = round(buy_count / total_trades, 4)
        fields['sell_pressure'] = round(sell_count / total_trades, 4)
        fields['buy_sell_ratio'] = round(buy_count / max(sell_count, 1), 2)
    else:
        fields['buy_pressure'] = 0.5
        fields['sell_pressure'] = 0.5
        fields['buy_sell_ratio'] = 1.0

    return fields

def _calculate_microstructure_fields(self, index: int) -> Dict[str, Any]:
    """计算市场微观结构字段"""
    fields = {}

    # 时间间隔分析
    if index > 0 and self.tick_history:
        time_diff = self._calculate_time_interval(index)
        fields['time_interval'] = time_diff

        # 成交频率 (每秒笔数)
        if time_diff > 0:
            fields['trade_frequency'] = round(1.0 / time_diff, 2)
        else:
            fields['trade_frequency'] = 0.0

    else:
        fields['time_interval'] = 0.0
        fields['trade_frequency'] = 0.0

    # 当日统计
    current_time = datetime.now().time()
    fields['session_type'] = self._determine_session_type(current_time)
    fields['time_slot'] = self._determine_time_slot(current_time)

    return fields
```

### **策略二：基于外部数据的字段补充** (优先级：2)

#### 2.1 基本面数据补充
```python
class FundamentalDataEnricher:
    def __init__(self):
        self.stock_info_cache = {}

    def enrich_with_fundamentals(self, tick_data: List[Dict]) -> List[Dict]:
        """补充基本面字段"""
        enriched_data = []

        stock_codes = list(set(tick.get('code', '') for tick in tick_data))

        # 批量获取股票信息
        stock_info = self._batch_get_stock_info(stock_codes)

        for tick in tick_data:
            code = tick.get('code', '')
            info = stock_info.get(code, {})

            # 补充基本面字段
            tick.update({
                'stock_name': info.get('name', ''),
                'industry': info.get('industry', ''),
                'sector': info.get('sector', ''),
                'market_cap': info.get('market_cap', 0),
                'pe_ratio': info.get('pe', 0),
                'pb_ratio': info.get('pb', 0)
            })

            enriched_data.append(tick)

        return enriched_data
```

#### 2.2 市场数据补充
```python
class MarketDataEnricher:
    def enrich_with_market_data(self, tick_data: List[Dict]) -> List[Dict]:
        """补充市场数据字段"""
        enriched_data = []

        for tick in tick_data:
            # 基于价格计算估值字段
            price = tick['price']

            tick.update({
                'price_level': self._determine_price_level(price),
                'volatility_5min': self._calculate_5min_volatility(tick_data),
                'momentum_1min': self._calculate_1min_momentum(tick_data),
                'rsi_14': self._calculate_rsi(tick_data),
                'bollinger_position': self._calculate_bb_position(tick_data)
            })

            enriched_data.append(tick)

        return enriched_data
```

### **策略三：增强字段验证和质量评估** (优先级：3)

#### 3.1 字段完整性评估器
```python
class MootdxCompletenessScorer:
    def __init__(self):
        self.required_fields = ['time', 'price', 'volume', 'amount', 'direction']
        self.enhanced_fields = [
            'price_change', 'price_change_pct', 'tick_direction',
            'volume_ma_10', 'buy_pressure', 'sell_pressure',
            'trade_frequency', 'time_interval'
        ]

    def calculate_completeness_score(self, tick_data: List[Dict]) -> Dict[str, Any]:
        """计算mootdx数据完整性评分"""
        total_ticks = len(tick_data)
        if total_ticks == 0:
            return {'score': 0, 'details': '无数据'}

        # 基础字段完整性
        base_completeness = self._check_base_fields_completeness(tick_data)

        # 增强字段完整性
        enhanced_completeness = self._check_enhanced_fields_completeness(tick_data)

        # 数据质量评估
        quality_score = self._assess_data_quality(tick_data)

        # 综合评分
        total_score = (
            base_completeness['score'] * 0.4 +      # 40%权重
            enhanced_completeness['score'] * 0.35 +  # 35%权重
            quality_score * 0.25                   # 25%权重
        )

        return {
            'score': round(total_score, 1),
            'grade': self._determine_grade(total_score),
            'base_completeness': base_completeness,
            'enhanced_completeness': enhanced_completeness,
            'quality_score': round(quality_score, 1),
            'details': {
                'total_ticks': total_ticks,
                'enhanced_fields_count': len(self.enhanced_fields),
                'quality_issues': self._identify_quality_issues(tick_data)
            }
        }
```

## 🔧 **实施步骤**

### **第一阶段：衍生字段计算引擎**
1. **开发MootdxFieldEnhancer核心模块**
2. **实现实时衍生字段计算算法**
3. **建立字段计算的性能优化机制**
4. **集成到现有FenbiEngine流程中**

### **第二阶段：外部数据补充**
1. **建立基本面数据缓存系统**
2. **开发市场数据实时计算模块**
3. **实现多维度数据融合机制**
4. **优化数据获取和缓存策略**

### **第三阶段：质量评估体系**
1. **完善字段完整性评估算法**
2. **建立数据质量监控机制**
3. **实现异常检测和告警系统**
4. **优化评分标准和权重配置**

## 📈 **预期效果**

### **短期效果 (1个月)**
- **字段数量**：从5个增加到20个
- **数据完整性评分**：从24/100提升至70/100
- **质量评级**：从E级提升至C级

### **中期效果 (3个月)**
- **字段数量**：增加到35个以上
- **数据完整性评分**：提升至85/100
- **质量评级**：达到B级水平
- **支持高级分析**：技术指标、风控等应用

### **长期效果 (6个月)**
- **字段数量**：达到50+个
- **数据完整性评分**：90/100以上
- **质量评级**：A级水平
- **智能化程度**：AI辅助字段补充和异常检测

## 💡 **关键成功因素**

1. **性能优先**：确保字段增强不影响实时性
2. **渐进实施**：分阶段逐步增加字段丰富度
3. **质量可控**：建立完整的字段验证机制
4. **扩展性强**：设计可插拔的字段计算模块
5. **成本效益**：基于现有数据最大化价值

## 📋 **字段映射详细表**

### **基础字段映射**
| mootdx字段 | 标准字段 | 数据类型 | 转换规则 |
|-----------|---------|----------|---------|
| time[0] | time | datetime | HH:MM:SS格式解析 |
| time[1] | price | float | 直接转换 |
| time[2] | volume | int | 直接转换 |
| time[3] | amount | float | 直接转换 |
| time[4] | direction | str | 1→B, -1→S, 0→N |

### **价格相关衍生字段**
| 字段名 | 计算方法 | 业务含义 |
|--------|----------|----------|
| price_change | current_price - prev_price | 相对前一笔价格变动 |
| price_change_pct | (price_change / prev_price) * 100 | 价格变动百分比 |
| price_high | max(price, price_history) | 当日最高价 |
| price_low | min(price, price_history) | 当日最低价 |
| price_level | 基于历史价格区间划分 | 价格水平等级 |

### **成交量相关衍生字段**
| 字段名 | 计算方法 | 业务含义 |
|-------------|----------|----------|
| cumulative_volume | sum(volume_history) + current_volume | 累计成交量 |
| volume_ratio | current_volume / cumulative_volume | 当笔成交量占比 |
| volume_ma_10 | 最近10笔成交量平均值 | 10周期移动平均 |
| is_large_order | volume > avg_volume * 2 | 大单标识 |

### **方向分析字段**
| 字段名 | 计算方法 | 业务含义 |
|-------------|----------|----------|
| tick_direction | 比较当前与前笔方向 | Tick方向(上/下/平) |
| buy_pressure | buy_count / total_trades | 买盘压力 |
| sell_pressure | sell_count / total_trades | 卖盘压力 |
| buy_sell_ratio | buy_count / max(sell_count, 1) | 买卖比率 |

### **市场微观结构字段**
| 字段名 | 计算方法 | 业务含义 |
|---------------------|----------|----------|
| time_interval | 当前时间 - 前一笔时间 | 时间间隔 |
| trade_frequency | 1 / time_interval | 成交频率 |
| session_type | 基于当前时间 | 交易时段 |
| time_slot | 基于当前时间划分 | 时间片段 |

## 🔧 **代码实现示例**

### **主要增强器类**
```python
class MootdxFieldEnhancer:
    """mootdx字段增强器主类"""

    def __init__(self):
        self.tick_history = []
        self.price_history = []
        self.volume_history = []
        self.direction_history = []
        self.cumulative_volume = 0

    def enhance_data(self, raw_data: List[List],
                     stock_code: str,
                     trade_date: datetime) -> List[Dict]:
        """增强mootdx数据并返回增强后的数据"""
        enhanced_data = []

        for i, tick in enumerate(raw_data):
            # 1. 基础字段映射
            enhanced_tick = {
                'time': self._parse_time(tick[0], trade_date),
                'price': float(tick[1]),
                'volume': int(tick[2]),
                'amount': float(tick[3]),
                'direction': self._convert_direction(tick[4]),
                'code': stock_code,
                'date': trade_date.date()
            }

            # 2. 衍生字段计算
            enhanced_tick.update(self._calculate_derived_fields(tick, i))

            # 3. 质量信息更新
            enhanced_tick.update(self._calculate_metrics(i))

            enhanced_data.append(enhanced_tick)

            # 4. 更新历史记录
            self._update_history(enhanced_tick)

        return enhanced_data

    def _calculate_derived_fields(self, tick: List, index: int) -> Dict[str, Any]:
        """计算所有衍生字段"""
        current_price = float(tick[1])
        current_volume = int(tick[2])
        current_direction = tick[4]

        # 集成各类衍生字段计算
        price_fields = self._calculate_price_fields(current_price, index)
        volume_fields = self._calculate_volume_fields(current_volume, index)
        direction_fields = self._calculate_direction_fields(current_direction, index)
        microstructure_fields = self._calculate_microstructure_fields(index)

        return {
            **price_fields,
            **volume_fields,
            **direction_fields,
            **microstructure_fields
        }
```

### **集成到FenbiEngine**
```python
class EnhancedFenbiEngine(FenbiEngine):
    """增强版Fenbi引擎"""

    def __init__(self, source_type: str = "mootdx", config: Optional[dict] = None):
        super().__init__(source_type, config)

        # 新增字段增强器
        self.field_enhancer = MootdxFieldEnhancer()

    async def get_tick_data(self, symbol: str, date: str,
                           market: str = None,
                           enable_field_enhancement: bool = True) -> List:
        """获取增强版分笔数据"""

        # 获取原始mootdx数据
        raw_data = await self._get_raw_data(symbol, date, market)

        if not raw_data:
            return []

        # 字段增强处理
        if enable_field_enhancement:
            try:
                # 解析交易日期
                trade_date = datetime.strptime(date, '%Y%m%d')

                # 字段增强
                enhanced_data = self.field_enhancer.enhance_data(
                    raw_data, symbol, trade_date
                )

                # 数据去重
                if hasattr(self, 'data_deduplicator'):
                    enhanced_data = self.data_deduplicator.remove_duplicates(
                        enhanced_data,
                        key_columns=['time', 'price', 'volume']
                    )

                return enhanced_data

            except Exception as e:
                print(f"[WARN] 字段增强失败: {e}")
                return raw_data

        return raw_data
```

## 📊 **性能优化策略**

### **内存管理**
```python
class OptimizedFieldEnhancer(MootdxFieldEnhancer):
    """优化版字段增强器"""

    def __init__(self, history_limit: int = 1000):
        super().__init__()
        self.history_limit = history_limit
        self._optimize_memory_usage()

    def _optimize_memory_usage(self):
        """优化内存使用"""
        # 使用更高效的数据结构
        self.price_history = collections.deque(maxlen=self.history_limit)
        self.volume_history = collections.deque(maxlen=self.history_limit)
        self.direction_history = collections.deque(maxlen=self.history_limit)

        # 预分配常用数据结构
        self.derived_fields_cache = {}

    def _update_history(self, tick: Dict):
        """更新历史记录（优化版）"""
        self.price_history.append(tick['price'])
        self.volume_history.append(tick['volume'])
        self.direction_history.append(self.tick.get('direction', 'N'))

        # 控制历史记录长度
        if len(self.price_history) > self.history_limit:
            self.price_history.popleft()
        if len(self.volume_history) > self.history_limit:
            self.volume_history.popleft()
        if len(self.direction_history) > self.history_limit:
            self.direction_history.popleft()

        self.cumulative_volume = sum(self.volume_history)
```

### **批量计算优化**
```python
def batch_enhance_data(self, raw_data_batches: List[List[List]],
                        stock_code: str, trade_date: datetime) -> List[List[Dict]]:
    """批量增强数据以提高性能"""
    enhanced_batches = []

    for batch in raw_data_batches:
        # 使用向量化操作进行批量计算
        prices = np.array([float(tick[1]) for tick in batch])
        volumes = np.array([int(tick[2]) for tick in batch])
        directions = np.array([int(tick[4]) for tick in batch])

        # 向量化计算衍生字段
        price_changes = np.diff(prices, prepend=0)
        cumulative_volumes = np.cumsum(volumes)

        # 批量构建增强数据
        enhanced_batch = []
        for i, tick in enumerate(batch):
            enhanced_tick = {
                # 基础字段
                'time': self._parse_time(tick[0], trade_date),
                'price': float(tick[1]),
                'volume': int(tick[2]),
                'amount': float(tick[3]),
                'direction': self._convert_direction(tick[4]),
                'code': stock_code,
                'date': trade_date.date(),

                # 向量化计算结果
                'price_change': round(price_changes[i], 4),
                'cumulative_volume': int(cumulative_volumes[i]),
                'tick_direction': self._determine_tick_direction_batch(
                    directions, i
                )
            }

            enhanced_batch.append(enhanced_tick)

        enhanced_batches.append(enhanced_batch)

    return enhanced_batches
```

通过这个comprehensive的mootdx接口字段完整性增强方案，可以显著提升分笔数据的分析价值，为更高级的金融分析提供更丰富的数据基础。