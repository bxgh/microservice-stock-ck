# A股数据采集系统详细实施指南

## 概述

本文档提供了A股数据采集系统中关键数据类型的详细实施指南，包括技术架构、配置参数、质量控制策略和监控告警机制的完整实现方案。

---

## 目录

1. [实时价格数据实施细节](#1-实时价格数据实施细节)
2. [财务数据实施细节](#2-财务数据实施细节)
3. [历史K线数据实施细节](#3-历史k线数据实施细节)
4. [资金流向数据实施细节](#4-资金流向数据实施细节)
5. [实施监控和运维](#5-实施监控和运维)

---

## 1. 实时价格数据实施细节

### 1.1 接口实施架构

```
实时价格采集系统架构:
┌─────────────────┐
│   调度引擎       │
│ (智能调度控制)   │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │接口适配器层 │
┌───┬────────┬───┐
│新浪│腾讯财经│东方│
│财经│(备用)  │财富│
└───┴────────┴───┘
    │     │     │
┌───┴─────┴─────┴───┐
│  数据质量检查层    │
│  (实时验证+修复)   │
└─────────────────┘
```

### 1.2 新浪财经API详细实施

#### 接口配置
```yaml
sina_finance_api:
  base_url: "https://hq.sinajs.cn/list="
  headers:
    User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    Referer: "https://finance.sina.com.cn/"
    Connection: "keep-alive"
  timeout: 5
  retry_count: 3
  rate_limit: 1  # 每秒最多1次请求
  batch_size: 50  # 每次最多50只股票

  proxy_settings:
    enabled: true
    http_proxy: "http://192.168.151.18:3128"
    https_proxy: "http://192.168.151.18:3128"
```

#### 数据解析规则
```python
# 新浪财经数据格式解析
# 原始格式: var hq_str_sh000001="上证指数,3200.15,3198.22,3205.67,3210.12,3195.23,0,0,321567890,12345678900"
# 字段映射:
field_mapping = {
    'name': 0,           # 指数名称
    'current_price': 1,  # 当前价
    'yesterday_close': 2, # 昨收价
    'open_price': 3,     # 开盘价
    'high_price': 4,     # 最高价
    'low_price': 5,      # 最低价
    'bid_price': 6,      # 买一价
    'ask_price': 7,      # 卖一价
    'volume': 8,         # 成交量(手)
    'amount': 9,         # 成交额(元)
    'date': 30,          # 日期
    'time': 31           # 时间
}

def parse_sina_data(raw_data):
    """解析新浪财经数据"""
    parsed_data = {}

    # 提取数据内容
    content = raw_data.split('"')[1]
    fields = content.split(',')

    for field_name, field_index in field_mapping.items():
        if field_index < len(fields):
            value = fields[field_index]

            # 数据类型转换
            if field_name in ['current_price', 'yesterday_close', 'open_price',
                            'high_price', 'low_price', 'bid_price', 'ask_price']:
                parsed_data[field_name] = float(value) if value else 0.0
            elif field_name in ['volume', 'amount']:
                parsed_data[field_name] = int(value) if value else 0
            else:
                parsed_data[field_name] = value

    return parsed_data
```

#### 数据质量检查规则
```python
def validate_sina_data(symbol, data):
    """新浪财经数据质量检查"""
    errors = []
    warnings = []

    # 1. 价格连续性检查
    if data['yesterday_close'] > 0:
        price_change = abs(data['current_price'] - data['yesterday_close']) / data['yesterday_close']
        if price_change > 0.10:  # 超过10%变化
            errors.append(f"价格跳跃过大: {price_change:.2%}")
        elif price_change > 0.05:  # 超过5%变化
            warnings.append(f"价格变化较大: {price_change:.2%}")

    # 2. OHLC逻辑检查
    if data['low_price'] > 0 and data['high_price'] > 0:
        if not (data['low_price'] <= data['open_price'] <= data['high_price']):
            errors.append("开盘价不在高低价范围内")

        if not (data['low_price'] <= data['current_price'] <= data['high_price']):
            errors.append("当前价不在高低价范围内")

        if data['low_price'] > data['high_price']:
            errors.append("最低价大于最高价")

    # 3. 买卖价差检查
    if data['bid_price'] > 0 and data['ask_price'] > 0:
        if data['bid_price'] > data['ask_price']:
            warnings.append("买一价高于卖一价")

    # 4. 成交量检查
    if data['volume'] < 0:
        errors.append("成交量为负数")
    elif data['volume'] == 0:
        warnings.append("成交量为零，可能为停牌")

    # 5. 成交额检查
    if data['amount'] < 0:
        errors.append("成交额为负数")
    elif data['amount'] == 0 and data['volume'] > 0:
        warnings.append("成交额为零但有成交量")

    # 6. 数据完整性检查
    required_fields = ['current_price', 'yesterday_close', 'open_price', 'high_price', 'low_price']
    missing_fields = [field for field in required_fields if data.get(field) is None]
    if missing_fields:
        errors.append(f"数据字段缺失: {missing_fields}")

    # 7. 交易状态检查
    if is_trading_time():
        if data['volume'] == 0:
            warnings.append("交易时间内成交量为零")

    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'quality_score': calculate_quality_score(errors, warnings)
    }

def calculate_quality_score(errors, warnings):
    """计算数据质量评分"""
    base_score = 100
    score = base_score

    # 每个错误扣10分
    score -= len(errors) * 10

    # 每个警告扣3分
    score -= len(warnings) * 3

    return max(0, score)
```

#### 实时监控实施
```python
class RealtimeDataMonitor:
    def __init__(self):
        self.sina_client = SinaFinanceClient()
        self.tencent_client = TencentFinanceClient()
        self.eastmoney_client = EastmoneyClient()

        self.monitoring_metrics = {
            'response_time': [],
            'data_quality_scores': [],
            'success_rates': [],
            'error_counts': []
        }

        self.alert_thresholds = {
            'response_time_critical': 10.0,  # 秒
            'response_time_warning': 5.0,
            'quality_score_critical': 80,
            'quality_score_warning': 90,
            'success_rate_critical': 0.95,
            'success_rate_warning': 0.98
        }

    def monitor_realtime_data(self, symbols):
        """监控实时数据"""
        for symbol in symbols:
            try:
                # 采集数据
                start_time = time.time()
                data = self._collect_data_with_fallback(symbol)
                response_time = time.time() - start_time

                # 数据质量检查
                validation_result = validate_sina_data(symbol, data)

                # 更新监控指标
                self._update_metrics(response_time, validation_result)

                # 检查告警条件
                self._check_alerts(symbol, validation_result, response_time)

                # 记录数据
                self._record_data(symbol, data, validation_result)

            except Exception as e:
                logger.error(f"监控股票 {symbol} 失败: {e}")
                self._handle_collection_error(symbol, e)

    def _collect_data_with_fallback(self, symbol):
        """带备用方案的数据采集"""
        # 尝试主接口 (新浪财经)
        try:
            data = self.sina_client.get_stock_data(symbol)
            return data
        except Exception as e:
            logger.warning(f"新浪财经获取 {symbol} 数据失败，尝试腾讯财经: {e}")

            # 尝试备用接口 (腾讯财经)
            try:
                data = self.tencent_client.get_stock_data(symbol)
                return data
            except Exception as e2:
                logger.error(f"腾讯财经获取 {symbol} 数据也失败，尝试东方财富: {e2}")

                # 尝试第三个接口 (东方财富)
                try:
                    data = self.eastmoney_client.get_stock_data(symbol)
                    return data
                except Exception as e3:
                    logger.error(f"所有接口都无法获取 {symbol} 数据: {e3}")
                    raise Exception(f"所有接口都无法获取股票 {symbol} 数据")
```

#### 告警规则配置
```yaml
alerts:
  critical:
    - name: "接口响应时间过长"
      condition: "response_time > 10"
      action: "立即切换备用接口"
      notification: ["email", "sms", "webhook"]

    - name: "数据质量严重异常"
      condition: "quality_score < 80"
      action: "立即重新获取数据"
      notification: ["email", "webhook"]

    - name: "接口完全失效"
      condition: "consecutive_failures >= 3"
      action: "立即切换到备用接口"
      notification: ["email", "sms", "webhook"]

  warning:
    - name: "接口响应时间较慢"
      condition: "response_time > 5 and response_time <= 10"
      action: "记录警告，监控趋势"
      notification: ["webhook"]

    - name: "数据质量轻微异常"
      condition: "quality_score >= 80 and quality_score < 90"
      action: "记录警告，持续监控"
      notification: ["webhook"]

    - name: "连续失败"
      condition: "consecutive_failures >= 1"
      action: "准备切换备用接口"
      notification: ["webhook"]
```

---

## 2. 财务数据实施细节

### 2.1 双接口协同实施策略

```
财务数据采集流程:
┌─────────────────┐
│   财报发布监控   │
│ (cninfo监控)     │
└─────────┬───────┘
          │ (财报发布)
    ┌─────┴─────┐
    │tushare主采集│
    │ (结构化数据)│
└───┬─────────────┘
    │
┌───┴─────────┐
│cninfo验证采集│
│ (原始公告)  │
└───┬─────────┘
    │
┌───┴─────────┐
│数据对比验证 │
│ (差异检测)  │
└─────────┬───┘
          │
┌─────────┴─────┐
│数据存储和索引 │
└─────────────────┘
```

### 2.2 tushare财务数据详细实施

#### 接口配置
```yaml
tushare_financial:
  base_url: "http://api.tushare.pro"
  token: "your_tushare_token"
  rate_limit: 200  # 每分钟200次
  rate_limit_period: 60  # 秒

  endpoints:
    income: "income"  # 利润表
    balancesheet: "balancesheet"  # 资产负债表
    cashflow: "cashflow"  # 现金流量表
    fina_indicator: "fina_indicator"  # 财务指标
    fina_audit: "fina_audit"  # 审计意见

  retry_policy:
    max_retries: 3
    backoff_factor: 2
    initial_delay: 1
    max_delay: 30
    timeout: 30

  cache_settings:
    enabled: true
    ttl: 3600  # 1小时缓存
    redis_host: "localhost"
    redis_port: 6379
    redis_db: 0
```

#### 财务数据标准化流程
```python
class FinancialDataNormalizer:
    def __init__(self):
        self.field_mappings = {
            'income_statement': {
                'revenue': ['total_revenue', 'revenue'],
                'operating_profit': ['operate_profit', 'operating_profit'],
                'total_profit': ['total_profit', 'total_profit'],
                'net_profit': ['n_income', 'net_profit'],
                'basic_eps': ['basic_eps', 'basic_eps']
            },
            'balance_sheet': {
                'total_assets': ['total_assets', 'total_assets'],
                'current_assets': ['total_cur_assets', 'current_assets'],
                'total_liabilities': ['total_liability', 'total_liabilities'],
                'current_liabilities': ['total_cur_liab', 'current_liabilities'],
                'total_equity': ['total_hldr_eqy_exc_min_int', 'total_equity']
            },
            'cash_flow': {
                'operating_cash_flow': ['c_f_oper_act', 'operating_cash_flow'],
                'investing_cash_flow': ['c_f_inv_act', 'investing_cash_flow'],
                'financing_cash_flow': ['c_f_fin_act', 'financing_cash_flow'],
                'net_cash_flow': ['net_cash_flows_act', 'net_cash_flow']
            }
        }

    def normalize_financial_data(self, raw_data, report_type, report_period):
        """财务数据标准化处理"""
        normalized = {
            'report_type': report_type,
            'report_period': report_period,
            'currency': 'CNY',
            'unit': '万元'
        }

        # 基础字段标准化
        normalized['ts_code'] = self._standardize_ts_code(raw_data['ts_code'])
        normalized['ann_date'] = self._standardize_date(raw_data['ann_date'])
        normalized['end_date'] = self._standardize_date(raw_data['end_date'])
        normalized['report_type'] = self._determine_report_type(report_period)

        # 根据报表类型进行字段映射
        if report_type in self.field_mappings:
            field_mapping = self.field_mappings[report_type]
            for standard_field, possible_fields in field_mapping.items():
                normalized[standard_field] = self._extract_field_value(raw_data, possible_fields)

        # 数据类型转换和验证
        normalized = self._convert_data_types(normalized)
        normalized = self._validate_financial_data(normalized)

        return normalized

    def _standardize_ts_code(self, ts_code):
        """标准化股票代码"""
        if not ts_code:
            return None

        # 确保格式为 XXXXXX.SZ 或 XXXXXX.SH
        if '.' not in ts_code:
            if ts_code.startswith('6'):
                return f"{ts_code}.SH"
            else:
                return f"{ts_code}.SZ"

        return ts_code.upper()

    def _standardize_date(self, date_str):
        """标准化日期格式"""
        if not date_str:
            return None

        try:
            # 支持多种日期格式
            if len(date_str) == 8:  # YYYYMMDD
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            elif '-' in date_str:  # YYYY-MM-DD
                return date_str
            else:
                # 尝试解析其他格式
                return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"日期格式化失败: {date_str}, 错误: {e}")
            return None

    def _extract_field_value(self, raw_data, possible_fields):
        """提取字段值"""
        for field in possible_fields:
            if field in raw_data and raw_data[field] is not None:
                value = raw_data[field]
                # 处理None和空字符串
                if value == '' or value == None:
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    logger.warning(f"无法转换为数字: {field} = {value}")
                    return 0.0
        return 0.0
```

#### 财务数据质量检查
```python
class FinancialDataQualityChecker:
    def __init__(self):
        self.validation_rules = {
            'income_statement': self._validate_income_statement,
            'balance_sheet': self._validate_balance_sheet,
            'cash_flow': self._validate_cash_flow
        }

    def validate_financial_data(self, data, report_type):
        """验证财务数据质量"""
        errors = []
        warnings = []

        # 通用验证
        generic_errors, generic_warnings = self._validate_generic_data(data)
        errors.extend(generic_errors)
        warnings.extend(generic_warnings)

        # 报表特定验证
        if report_type in self.validation_rules:
            specific_errors, specific_warnings = self.validation_rules[report_type](data)
            errors.extend(specific_errors)
            warnings.extend(specific_warnings)

        # 计算质量评分
        quality_score = self._calculate_quality_score(errors, warnings)

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'quality_score': quality_score
        }

    def _validate_income_statement(self, data):
        """验证利润表数据"""
        errors = []
        warnings = []

        # 基本逻辑检查
        if data['revenue'] < 0:
            errors.append("营业收入为负数")

        if data['total_profit'] < 0 and data['net_profit'] > 0:
            warnings.append("利润总额为负但净利润为正，可能有异常")

        # 盈利能力检查
        if data['revenue'] > 0:
            gross_margin = (data['revenue'] - data.get('operating_cost', 0)) / data['revenue']
            if gross_margin < -0.5:  # 毛利率为负超过50%
                warnings.append(f"毛利率异常: {gross_margin:.2%}")

            net_margin = data['net_profit'] / data['revenue']
            if net_margin < -1:  # 净利率为负超过100%
                warnings.append(f"净利率异常: {net_margin:.2%}")

        return errors, warnings

    def _validate_balance_sheet(self, data):
        """验证资产负债表数据"""
        errors = []
        warnings = []

        # 基本会计等式检查
        if abs(data['total_assets'] - (data['total_liabilities'] + data['total_equity'])) > 0.01:
            errors.append("资产负债表不平衡: 资产 != 负债 + 所有者权益")

        # 流动性检查
        if data['current_liabilities'] > 0:
            current_ratio = data['current_assets'] / data['current_liabilities']
            if current_ratio < 0.5:
                warnings.append(f"流动比率过低: {current_ratio:.2f}")
            elif current_ratio > 5:
                warnings.append(f"流动比率过高: {current_ratio:.2f}")

        # 资产结构检查
        if data['total_assets'] > 0:
            current_asset_ratio = data['current_assets'] / data['total_assets']
            if current_asset_ratio > 0.9:
                warnings.append(f"流动资产占比过高: {current_asset_ratio:.2%}")
            elif current_asset_ratio < 0.1:
                warnings.append(f"流动资产占比过低: {current_asset_ratio:.2%}")

        return errors, warnings

    def _validate_cash_flow(self, data):
        """验证现金流量表数据"""
        errors = []
        warnings = []

        # 现金流平衡检查
        net_cash_flow = data['operating_cash_flow'] + data['investing_cash_flow'] + data['financing_cash_flow']
        if abs(net_cash_flow - data.get('net_cash_flow', 0)) > 0.01:
            warnings.append("现金流净额计算不一致")

        # 经营现金流检查
        if data['net_profit'] > 0 and data['operating_cash_flow'] < 0:
            warnings.append("净利润为正但经营现金流为负，需关注盈利质量")

        return errors, warnings
```

### 2.3 cninfo官方数据验证实施

#### 公告监控策略
```python
class AnnouncementMonitor:
    def __init__(self):
        self.cninfo_client = CninfoApiClient()
        self.tushare_client = TushareClient()
        self.monitored_symbols = []  # 监控股票列表
        self.announcement_types = {
            'annual_report': '年度报告',
            'semi_annual_report': '半年度报告',
            'quarterly_report_q1': '一季度报告',
            'quarterly_report_q3': '三季度报告'
        }
        self.monitoring_interval = 300  # 5分钟检查一次

    def start_monitoring(self):
        """启动公告监控"""
        logger.info("启动财报公告监控")

        while True:
            try:
                # 获取最新公告
                new_announcements = self._get_latest_announcements()

                # 处理新公告
                for announcement in new_announcements:
                    if self._should_process_announcement(announcement):
                        self._process_announcement(announcement)

                # 等待下次检查
                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"公告监控异常: {e}")
                time.sleep(60)  # 异常时等待1分钟再重试

    def _get_latest_announcements(self):
        """获取最新公告"""
        announcements = []

        for report_type, type_name in self.announcement_types.items():
            try:
                # 获取最近24小时的公告
                end_date = datetime.now()
                start_date = end_date - timedelta(days=1)

                type_announcements = self.cninfo_client.get_announcements(
                    announcement_type=report_type,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )

                announcements.extend(type_announcements)

            except Exception as e:
                logger.error(f"获取 {type_name} 公告失败: {e}")

        return announcements

    def _should_process_announcement(self, announcement):
        """判断是否应该处理该公告"""
        # 检查是否在监控股票列表中
        if announcement['symbol'] not in self.monitored_symbols:
            return False

        # 检查是否已经处理过
        if self._is_announcement_processed(announcement):
            return False

        return True

    def _process_announcement(self, announcement):
        """处理公告"""
        symbol = announcement['symbol']
        report_date = announcement['report_date']
        announcement_id = announcement['announcement_id']

        logger.info(f"处理财报公告: {symbol} {report_date} {announcement_id}")

        try:
            # 1. 获取原始公告
            original_report = self.cninfo_client.get_announcement_detail(announcement_id)

            # 2. 触发tushare数据更新
            self._trigger_tushare_update(symbol, report_date)

            # 3. 等待tushare数据更新
            time.sleep(30)  # 等待30秒

            # 4. 获取tushare数据
            tushare_data = self._get_tushare_financial_data(symbol, report_date)

            # 5. 对比验证数据
            discrepancies = self._validate_data_consistency(tushare_data, original_report)

            # 6. 处理验证结果
            self._handle_validation_result(symbol, report_date, discrepancies)

            # 7. 标记公告已处理
            self._mark_announcement_processed(announcement)

        except Exception as e:
            logger.error(f"处理公告失败: {symbol} {report_date} {e}")
            self._create_manual_review_task(announcement, str(e))
```

#### 数据对比验证详细实施
```python
class FinancialDataValidator:
    def __init__(self):
        self.tolerance_thresholds = {
            'revenue': 0.02,      # 营业收入2%容差
            'net_profit': 0.03,   # 净利润3%容差
            'total_assets': 0.01, # 总资产1%容差
            'total_liabilities': 0.01,  # 总负债1%容差
            'cash_flow': 0.05     # 现金流5%容差
        }

    def validate_data_consistency(self, tushare_data, cninfo_data):
        """验证财务数据一致性"""
        discrepancies = []

        # 提取关键财务指标
        tushare_indicators = self._extract_key_indicators(tushare_data)
        cninfo_indicators = self._extract_key_indicators(cninfo_data)

        # 对比各项指标
        for indicator in tushare_indicators:
            if indicator in cninfo_indicators:
                tushare_value = tushare_indicators[indicator]
                cninfo_value = cninfo_indicators[indicator]

                discrepancy = self._calculate_discrepancy(
                    indicator, tushare_value, cninfo_value
                )

                if discrepancy:
                    discrepancies.append(discrepancy)

        return discrepancies

    def _extract_key_indicators(self, data):
        """提取关键财务指标"""
        indicators = {}

        # 利润表指标
        if 'revenue' in data:
            indicators['revenue'] = data['revenue']
        if 'net_profit' in data:
            indicators['net_profit'] = data['net_profit']
        if 'operating_profit' in data:
            indicators['operating_profit'] = data['operating_profit']

        # 资产负债表指标
        if 'total_assets' in data:
            indicators['total_assets'] = data['total_assets']
        if 'total_liabilities' in data:
            indicators['total_liabilities'] = data['total_liabilities']
        if 'total_equity' in data:
            indicators['total_equity'] = data['total_equity']

        # 现金流量表指标
        if 'operating_cash_flow' in data:
            indicators['operating_cash_flow'] = data['operating_cash_flow']
        if 'investing_cash_flow' in data:
            indicators['investing_cash_flow'] = data['investing_cash_flow']
        if 'financing_cash_flow' in data:
            indicators['financing_cash_flow'] = data['financing_cash_flow']

        return indicators

    def _calculate_discrepancy(self, indicator, tushare_value, cninfo_value):
        """计算差异"""
        if tushare_value == 0 and cninfo_value == 0:
            return None

        if tushare_value == 0:
            return {
                'indicator': indicator,
                'tushare_value': tushare_value,
                'cninfo_value': cninfo_value,
                'absolute_diff': cninfo_value,
                'relative_diff': float('inf'),
                'severity': 'high'
            }

        absolute_diff = abs(tushare_value - cninfo_value)
        relative_diff = absolute_diff / abs(tushare_value)

        # 判断严重程度
        tolerance = self.tolerance_thresholds.get(indicator, 0.02)
        if relative_diff > tolerance * 3:
            severity = 'high'
        elif relative_diff > tolerance:
            severity = 'medium'
        else:
            severity = 'low'

        return {
            'indicator': indicator,
            'tushare_value': tushare_value,
            'cninfo_value': cninfo_value,
            'absolute_diff': absolute_diff,
            'relative_diff': relative_diff,
            'severity': severity
        }

    def _handle_validation_result(self, symbol, report_date, discrepancies):
        """处理验证结果"""
        if not discrepancies:
            logger.info(f"数据验证通过: {symbol} {report_date}")
            return

        # 按严重程度分类
        high_discrepancies = [d for d in discrepancies if d['severity'] == 'high']
        medium_discrepancies = [d for d in discrepancies if d['severity'] == 'medium']
        low_discrepancies = [d for d in discrepancies if d['severity'] == 'low']

        # 处理高度差异
        if high_discrepancies:
            self._handle_high_discrepancies(symbol, report_date, high_discrepancies)

        # 处理中度差异
        if medium_discrepancies:
            self._handle_medium_discrepancies(symbol, report_date, medium_discrepancies)

        # 记录低度差异
        if low_discrepancies:
            self._log_low_discrepancies(symbol, report_date, low_discrepancies)

    def _handle_high_discrepancies(self, symbol, report_date, discrepancies):
        """处理高度差异"""
        # 立即告警
        alert_message = f"""
        财务数据高度差异告警:
        股票: {symbol}
        报告期: {report_date}
        差异详情:
        """

        for discrepancy in discrepancies:
            alert_message += f"""
            指标: {discrepancy['indicator']}
            Tushare值: {discrepancy['tushare_value']:,.2f}
            Cninfo值: {discrepancy['cninfo_value']:,.2f}
            相对差异: {discrepancy['relative_diff']:.2%}
            """

        self._send_alert(alert_message, 'critical')

        # 创建人工审核任务
        self._create_manual_review_task({
            'symbol': symbol,
            'report_date': report_date,
            'discrepancies': discrepancies,
            'severity': 'high',
            'created_at': datetime.now()
        })
```

---

## 3. 历史K线数据实施细节

### 3.1 baostock历史数据深度实施

#### 接口配置和优化
```yaml
baostock_config:
  login_url: "http://baostock.com/api/v1/login"
  data_url: "http://baostock.com/api/v1/history"

  # 登录配置
  login_params:
    username: "your_username"
    password: "your_password"

  # 请求限制
  rate_limit: 10  # 每秒10次请求
  batch_size: 100  # 每次获取100只股票
  max_retries: 5
  timeout: 30
  connection_pool_size: 20

  # 数据获取参数
  default_fields: [
    "date", "code", "open", "high", "low", "close",
    "preclose", "volume", "amount", "adjustflag",
    "turn", "tradestatus", "pctChg", "isST"
  ]

  # 复权处理
  adjustflag:
    "3": "后复权"  # 默认后复权
    "2": "前复权"
    "1": "不复权"

  # 缓存配置
  cache:
    enabled: true
    redis_host: "localhost"
    redis_port: 6379
    redis_db: 1
    cache_ttl: 86400  # 24小时缓存

  # 数据存储配置
  storage:
    batch_insert_size: 1000
    compression: true
    backup_enabled: true
```

#### 历史数据批量获取策略
```python
class HistoricalDataCollector:
    def __init__(self):
        self.baostock_client = BaostockClient()
        self.data_storage = DataStorage()
        self.progress_tracker = ProgressTracker()
        self.quality_checker = DataQualityChecker()

        self.collection_config = {
            'start_date': '2005-01-01',  # 从2005年开始
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'frequency': 'd',  # 日线数据
            'adjustflag': 3  # 后复权
        }

    def collect_all_historical_data(self, symbols=None):
        """批量获取所有股票历史数据"""
        if symbols is None:
            # 获取所有A股列表
            symbols = self._get_all_a_share_symbols()

        logger.info(f"开始获取 {len(symbols)} 只股票的历史数据")

        # 按股票分组，避免单次请求过大
        symbol_groups = self._group_symbols(symbols, group_size=100)

        total_groups = len(symbol_groups)
        for i, group in enumerate(symbol_groups, 1):
            logger.info(f"处理第 {i}/{total_groups} 组股票，共 {len(group)} 只")

            try:
                # 获取该组股票的历史数据
                group_data = self._get_group_historical_data(
                    group,
                    self.collection_config['start_date'],
                    self.collection_config['end_date']
                )

                if group_data:
                    # 数据质量检查和增强
                    enhanced_data = self._enhance_data_quality(group_data)

                    # 批量存储
                    self._batch_store_data(enhanced_data)

                    # 更新进度
                    self.progress_tracker.update_progress(i, total_groups, len(group))

                # 控制请求频率
                time.sleep(1)  # 避免请求过快

            except Exception as e:
                logger.error(f"获取股票组 {group} 历史数据失败: {e}")
                # 记录失败股票，后续重试
                self._record_failed_symbols(group, e)

        # 处理失败的股票
        self._retry_failed_symbols()

        logger.info("历史数据采集完成")

    def _get_group_historical_data(self, symbols, start_date, end_date):
        """获取一组股票的历史数据"""
        all_data = []

        # 登录baostock
        if not self.baostock_client.login():
            raise Exception("baostock登录失败")

        try:
            # 构建查询代码
            code_string = ",".join(symbols)

            # 查询历史数据
            rs = self.baostock_client.query_history_k_data_plus(
                code=code_string,
                start_date=start_date,
                end_date=end_date,
                frequency=self.collection_config['frequency'],
                adjustflag=self.collection_config['adjustflag'],
                fields=",".join(self.collection_config['default_fields'])
            )

            if rs.error_code != '0':
                raise Exception(f"baostock查询失败: {rs.error_msg}")

            # 解析返回数据
            if rs.data() and len(rs.data()) > 0:
                all_data = self._parse_baostock_response(rs)
                logger.info(f"获取到 {len(all_data)} 条历史数据")
            else:
                logger.warning(f"未获取到数据: {code_string}")

        finally:
            # 登出baostock
            self.baostock_client.logout()

        return all_data

    def _parse_baostock_response(self, rs):
        """解析baostock响应数据"""
        data = []
        fields = rs.fields()

        for row in rs.data():
            record = {}
            for i, field in enumerate(fields):
                if i < len(row):
                    value = row[i]

                    # 数据类型转换
                    if field in ['open', 'high', 'low', 'close', 'preclose', 'pctChg']:
                        record[field] = float(value) if value else 0.0
                    elif field in ['volume', 'amount', 'turn']:
                        record[field] = int(value) if value else 0
                    elif field in ['adjustflag', 'tradestatus', 'isST']:
                        record[field] = int(value) if value else 0
                    else:
                        record[field] = value

            data.append(record)

        return data

    def _enhance_data_quality(self, raw_data):
        """增强数据质量"""
        enhanced_data = []

        for record in raw_data:
            try:
                enhanced_record = self._enhance_single_record(record)

                # 数据质量检查
                if self._validate_record_quality(enhanced_record):
                    enhanced_data.append(enhanced_record)
                else:
                    logger.warning(f"数据质量检查失败，跳过: {record['code']} {record['date']}")

            except Exception as e:
                logger.error(f"增强数据质量失败: {record['code']} {record['date']}, 错误: {e}")

        return enhanced_data

    def _enhance_single_record(self, record):
        """增强单条记录"""
        enhanced_record = record.copy()

        # 1. 标准化股票代码
        enhanced_record['standard_code'] = self._standardize_stock_code(record['code'])

        # 2. 标准化日期
        enhanced_record['standard_date'] = self._standardize_date(record['date'])

        # 3. 计算额外字段
        enhanced_record['price_change'] = record['close'] - record['preclose']
        enhanced_record['price_change_pct'] = record['pctChg'] / 100.0 if record['pctChg'] else 0.0
        enhanced_record['turnover_rate'] = record['turn'] / 100.0 if record['turn'] else 0.0

        # 4. 添加数据质量标记
        enhanced_record['data_quality'] = self._assess_data_quality(record)

        # 5. 添加业务标记
        enhanced_record = self._add_business_flags(enhanced_record)

        return enhanced_record

    def _add_business_flags(self, record):
        """添加业务标记"""
        # 停牌标记
        if record.get('tradestatus', 0) == 0:
            record['is_suspended'] = True
        else:
            record['is_suspended'] = False

        # ST标记
        if record.get('isST', 0) == 1:
            record['is_st'] = True
        else:
            record['is_st'] = False

        # 涨跌停标记
        price_change_pct = record.get('price_change_pct', 0)
        if price_change_pct >= 0.095:  # 接近涨停
            record['is_limit_up'] = True
        elif price_change_pct <= -0.095:  # 接近跌停
            record['is_limit_down'] = True

        # 异常价格标记
        if self._is_price_anomaly(record):
            record['is_price_anomaly'] = True

        return record
```

#### 数据质量增强处理
```python
def detect_and_fix_price_anomalies(record):
    """检测和修复价格异常"""
    fixed_record = record.copy()

    # 1. 开盘价异常检查和修复
    if record['open'] > record['high'] or record['open'] < record['low']:
        logger.warning(f"开盘价异常: {record['code']} {record['date']} open={record['open']}, high={record['high']}, low={record['low']}")

        # 尝试修复：使用前一日收盘价
        previous_close = get_previous_close_price(record['code'], record['date'])
        if previous_close and previous_close > 0:
            fixed_record['open'] = previous_close
            fixed_record['price_fixed'] = True
            fixed_record['fix_reason'] = '开盘价异常，使用前收盘价修复'

    # 2. 收盘价异常检测
    if record['close'] > record['high'] or record['close'] < record['low']:
        logger.warning(f"收盘价异常: {record['code']} {record['date']} close={record['close']}, high={record['high']}, low={record['low']}")

        # 标记异常，但保留原数据
        fixed_record['close_anomaly'] = True
        fixed_record['anomaly_reason'] = '收盘价超出高低价范围'

    # 3. 价格跳跃检测
    if record['preclose'] > 0:
        price_change_ratio = abs(record['close'] - record['preclose']) / record['preclose']

        if price_change_ratio > 0.20:  # 超过20%变化
            logger.warning(f"价格跳跃过大: {record['code']} {record['date']} {price_change_ratio:.2%}")
            fixed_record['large_price_move'] = True
            fixed_record['price_change_ratio'] = price_change_ratio

            # 验证是否为除权除息日
            if not is_ex_dividend_date(record['date'], record['code']):
                fixed_record['unexplained_price_move'] = True
                fixed_record['requires_manual_review'] = True

    # 4. 成交量异常检测
    if record['volume'] < 0:
        logger.error(f"成交量为负数: {record['code']} {record['date']} volume={record['volume']}")
        fixed_record['volume'] = 0
        fixed_record['volume_fixed'] = True

    # 5. 成交额异常检测
    if record['amount'] < 0:
        logger.error(f"成交额为负数: {record['code']} {record['date']} amount={record['amount']}")
        fixed_record['amount'] = 0
        fixed_record['amount_fixed'] = True

    # 6. 成交额与成交量匹配检查
    if record['volume'] > 0 and record['amount'] >= 0:
        avg_price = record['amount'] / (record['volume'] * 100)  # 转换为元

        # 平均价格应该在最低价和最高价之间
        if not (record['low'] <= avg_price <= record['high']):
            logger.warning(f"成交额与成交量不匹配: {record['code']} {record['date']} avg_price={avg_price}, low={record['low']}, high={record['high']}")
            fixed_record['amount_volume_mismatch'] = True

    return fixed_record

def validate_data_completeness(record):
    """验证数据完整性"""
    required_fields = ['date', 'code', 'open', 'high', 'low', 'close', 'volume']

    for field in required_fields:
        if field not in record or record[field] is None:
            logger.warning(f"数据字段缺失: {field}")
            return False

        # 检查数值字段是否为有效值
        if field in ['open', 'high', 'low', 'close', 'volume']:
            if isinstance(record[field], (int, float)) and record[field] < 0:
                logger.warning(f"数值字段为负数: {field}={record[field]}")
                return False

    return True

def is_ex_dividend_date(date, code):
    """检查是否为除权除息日"""
    # 这里需要查询除权除息日历
    # 可以从数据库或API获取
    dividend_calendar = get_dividend_calendar(code)

    for dividend_event in dividend_calendar:
        if dividend_event['ex_date'] == date:
            return True

    return False
```

---

## 4. 资金流向数据实施细节

### 4.1 资金流向数据采集架构

```
资金流向数据采集流程:
┌─────────────────┐
│   实时监控调度   │
│ (交易时间内运行) │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │东方财富API   │
│ (主力资金监控) │
└───┬─────────────┘
    │
┌───┴─────────┐
│资金流向计算 │
│ (分类计算)  │
└───┬─────────┘
    │
┌───┴─────────┐
│趋势分析    │
│ (短期趋势)  │
└───┬─────────┘
    │
┌───┴─────────┐
│数据存储    │
│ (实时存储)  │
└─────────────────┘
```

### 4.2 东方财富资金流向详细实施

#### 接口配置
```yaml
eastmoney_fundflow:
  base_url: "https://push2.eastmoney.com/api/qt/stock/fflow"

  headers:
    User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    Referer: "https://quote.eastmoney.com/"
    Accept: "application/json, text/plain, */*"
    Accept-Language: "zh-CN,zh;q=0.9,en;q=0.8"
    Connection: "keep-alive"

  rate_limit: 5  # 每秒5次请求
  timeout: 10

  endpoints:
    individual_stock: "kline/get"  # 个股资金流向
    market_overall: "klinedervast/get"  # 市场整体资金流向
    sector_fundflow: "secid/get"  # 板块资金流向

  request_params:
    fields1: "f1,f2,f3,f7"
    fields2: "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63"
    klt: "101"  # 日线
    fqt: "1"    # 前复权
    lmt: "1"    # 最新数据

  retry_policy:
    max_retries: 3
    backoff_factor: 1.5
    initial_delay: 1
    max_delay: 30

  data_processing:
    batch_size: 100
    update_interval: 60  # 秒
    trend_analysis_days: 5
```

#### 资金流向分类计算
```python
class FundFlowCalculator:
    def __init__(self):
        self.classification_rules = {
            'super_large_order': {
                'threshold': 1000000,  # 100万以上
                'label': '超大单',
                'weight': 0.4
            },
            'large_order': {
                'threshold': 200000,   # 20万-100万
                'label': '大单',
                'weight': 0.3
            },
            'medium_order': {
                'threshold': 40000,    # 4万-20万
                'label': '中单',
                'weight': 0.2
            },
            'small_order': {
                'threshold': 0,        # 4万以下
                'label': '小单',
                'weight': 0.1
            }
        }

    def calculate_fund_flow(self, symbol, date=None):
        """计算个股资金流向"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # 获取原始资金流向数据
        raw_flow_data = self._get_raw_fund_flow_data(symbol, date)

        if not raw_flow_data:
            return self._get_empty_fund_flow(symbol, date)

        # 按订单大小分类计算
        classified_flow = self._classify_fund_flow(raw_flow_data)

        # 计算各类资金流向
        fund_flow_result = {}

        for order_type, config in self.classification_rules.items():
            fund_flow_result[order_type] = self._calculate_order_flow(
                classified_flow[order_type], config['label']
            )

        # 计算主力资金流向
        fund_flow_result['main_force'] = self._calculate_main_force_flow(fund_flow_result)

        # 计算资金流向趋势
        fund_flow_result['trend'] = self._calculate_flow_trend(symbol, date)

        # 计算资金流向强度
        fund_flow_result['intensity'] = self._calculate_flow_intensity(fund_flow_result)

        # 添加元数据
        fund_flow_result['symbol'] = symbol
        fund_flow_result['date'] = date
        fund_flow_result['calculated_at'] = datetime.now().isoformat()

        return fund_flow_result

    def _classify_fund_flow(self, raw_data):
        """按订单大小分类资金流向数据"""
        classified = {
            'super_large_order': {'buy_amount': 0, 'sell_amount': 0, 'net_amount': 0},
            'large_order': {'buy_amount': 0, 'sell_amount': 0, 'net_amount': 0},
            'medium_order': {'buy_amount': 0, 'sell_amount': 0, 'net_amount': 0},
            'small_order': {'buy_amount': 0, 'sell_amount': 0, 'net_amount': 0}
        }

        # 根据东方财富数据格式解析
        if 'f51' in raw_data and 'f52' in raw_data:
            # f51: 主力净流入-净额
            # f52: 超大单净流入-净额
            # f53: 大单净流入-净额
            # f54: 中单净流入-净额
            # f55: 小单净流入-净额

            # 直接使用东方财富的分类结果
            classified['super_large_order']['net_amount'] = float(raw_data.get('f52', 0))
            classified['large_order']['net_amount'] = float(raw_data.get('f53', 0))
            classified['medium_order']['net_amount'] = float(raw_data.get('f54', 0))
            classified['small_order']['net_amount'] = float(raw_data.get('f55', 0))

            # f62-f66: 主力净流入-净额的明细
            # f62: 主力净流入-超大单
            # f63: 主力净流入-大单
            # f64: 主力净流入-中单
            # f65: 主力净流入-小单

            # 计算买入卖出金额（估算）
            net_amount = classified['super_large_order']['net_amount']
            # 假设买卖比例，实际情况可能需要更复杂的计算
            buy_ratio = 0.6 if net_amount > 0 else 0.4
            sell_ratio = 1 - buy_ratio

            total_amount = abs(net_amount)
            classified['super_large_order']['buy_amount'] = total_amount * buy_ratio
            classified['super_large_order']['sell_amount'] = total_amount * sell_ratio

            # 类似处理其他类型
            for order_type in ['large_order', 'medium_order', 'small_order']:
                net_amount = classified[order_type]['net_amount']
                buy_ratio = 0.6 if net_amount > 0 else 0.4
                sell_ratio = 1 - buy_ratio
                total_amount = abs(net_amount)
                classified[order_type]['buy_amount'] = total_amount * buy_ratio
                classified[order_type]['sell_amount'] = total_amount * sell_ratio

        return classified

    def _calculate_main_force_flow(self, fund_flow_result):
        """计算主力资金流向"""
        # 主力资金 = 超大单 + 大单
        main_force_buy = (
            fund_flow_result['super_large_order']['buy_amount'] +
            fund_flow_result['large_order']['buy_amount']
        )
        main_force_sell = (
            fund_flow_result['super_large_order']['sell_amount'] +
            fund_flow_result['large_order']['sell_amount']
        )
        main_force_net = main_force_buy - main_force_sell

        return {
            'buy_amount': main_force_buy,
            'sell_amount': main_force_sell,
            'net_amount': main_force_net,
            'net_amount_ratio': self._calculate_ratio(main_force_net, main_force_buy + main_force_sell)
        }

    def _calculate_flow_trend(self, symbol, date):
        """计算资金流向趋势"""
        # 获取最近5天的资金流向数据
        end_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=5)

        historical_flows = self._get_historical_fund_flows(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            date
        )

        if not historical_flows or len(historical_flows) < 3:
            return {
                'trend': 'unknown',
                'strength': 0,
                'direction': 'neutral',
                'consistency': 0
            }

        # 计算趋势
        net_amounts = [flow['main_force']['net_amount'] for flow in historical_flows]

        # 趋势方向
        if len(net_amounts) >= 2:
            recent_avg = sum(net_amounts[-3:]) / min(3, len(net_amounts))
            earlier_avg = sum(net_amounts[:-3]) / max(1, len(net_amounts) - 3)

            if recent_avg > earlier_avg * 1.2:
                direction = 'strong_inflow'
                trend = 'up'
            elif recent_avg < earlier_avg * 0.8:
                direction = 'strong_outflow'
                trend = 'down'
            else:
                direction = 'stable'
                trend = 'neutral'
        else:
            direction = 'neutral'
            trend = 'neutral'

        # 趋势强度（基于标准差）
        if len(net_amounts) > 1:
            strength = statistics.stdev(net_amounts) / (abs(statistics.mean(net_amounts)) + 1)
        else:
            strength = 0

        # 一致性（连续同向天数）
        consistency = self._calculate_consistency(net_amounts)

        return {
            'trend': trend,
            'strength': min(1.0, strength / 0.5),  # 标准化到0-1
            'direction': direction,
            'consistency': consistency,
            'data_points': len(historical_flows)
        }

    def _calculate_flow_intensity(self, fund_flow_result):
        """计算资金流向强度"""
        total_buy = sum(flow['buy_amount'] for flow in fund_flow_result.values() if 'buy_amount' in flow)
        total_sell = sum(flow['sell_amount'] for flow in fund_flow_result.values() if 'sell_amount' in flow)
        total_amount = total_buy + total_sell

        if total_amount == 0:
            return {
                'overall_intensity': 0,
                'main_force_intensity': 0,
                'retail_intensity': 0,
                'classification': 'no_activity'
            }

        # 主力资金强度
        main_force_amount = fund_flow_result['main_force']['buy_amount'] + fund_flow_result['main_force']['sell_amount']
        main_force_intensity = main_force_amount / total_amount

        # 散户资金强度（中单+小单）
        retail_amount = (
            fund_flow_result['medium_order']['buy_amount'] + fund_flow_result['medium_order']['sell_amount'] +
            fund_flow_result['small_order']['buy_amount'] + fund_flow_result['small_order']['sell_amount']
        )
        retail_intensity = retail_amount / total_amount

        # 整体强度（基于总金额）
        if total_amount > 100000000:  # 超过1亿
            overall_intensity = min(1.0, total_amount / 1000000000)  # 相对于10亿
        elif total_amount > 10000000:  # 超过1000万
            overall_intensity = total_amount / 100000000
        else:
            overall_intensity = total_amount / 10000000

        # 分类
        if overall_intensity > 0.8:
            classification = 'very_high'
        elif overall_intensity > 0.5:
            classification = 'high'
        elif overall_intensity > 0.2:
            classification = 'medium'
        elif overall_intensity > 0.05:
            classification = 'low'
        else:
            classification = 'very_low'

        return {
            'overall_intensity': overall_intensity,
            'main_force_intensity': main_force_intensity,
            'retail_intensity': retail_intensity,
            'total_amount': total_amount,
            'classification': classification
        }
```

#### 资金流向异常监控
```python
class FundFlowMonitor:
    def __init__(self):
        self.anomaly_thresholds = {
            'sudden_large_inflow': 50000000,     # 5000万突然净流入
            'sudden_large_outflow': -50000000,   # 5000万突然净流出
            'continuous_inflow_days': 5,         # 连续5天净流入
            'continuous_outflow_days': 5,        # 连续5天净流出
            'abnormal_flow_ratio': 0.3,          # 净流入率超过30%
            'unusual_main_force_ratio': 0.8,     # 主力资金占比超过80%
            'intensity_spike': 5.0              # 强度突增5倍
        }

        self.alert_cooldown = 300  # 5分钟冷却时间
        self.last_alerts = {}  # 记录上次告警时间

    def monitor_fund_flow_anomalies(self, symbol, current_flow, historical_flows):
        """监控资金流向异常"""
        anomalies = []

        # 1. 突然大额净流入/流出
        sudden_flow_anomaly = self._check_sudden_flow_anomaly(symbol, current_flow)
        if sudden_flow_anomaly:
            anomalies.append(sudden_flow_anomaly)

        # 2. 连续净流入/流出天数
        continuous_flow_anomaly = self._check_continuous_flow_anomaly(symbol, historical_flows)
        if continuous_flow_anomaly:
            anomalies.append(continuous_flow_anomaly)

        # 3. 异常净流入率
        ratio_anomaly = self._check_flow_ratio_anomaly(symbol, current_flow)
        if ratio_anomaly:
            anomalies.append(ratio_anomaly)

        # 4. 主力资金异常
        main_force_anomaly = self._check_main_force_anomaly(symbol, current_flow)
        if main_force_anomaly:
            anomalies.append(main_force_anomaly)

        # 5. 强度异常
        intensity_anomaly = self._check_intensity_anomaly(symbol, current_flow, historical_flows)
        if intensity_anomaly:
            anomalies.append(intensity_anomaly)

        return anomalies

    def _check_sudden_flow_anomaly(self, symbol, current_flow):
        """检查突然大额资金流向异常"""
        net_amount = current_flow['main_force']['net_amount']

        if abs(net_amount) > self.anomaly_thresholds['sudden_large_inflow']:
            # 检查是否需要冷却（避免重复告警）
            alert_key = f"sudden_flow_{symbol}"
            if self._should_send_alert(alert_key):
                return {
                    'type': 'sudden_large_flow',
                    'description': f"突然大额净流入: {net_amount:,.0f}元" if net_amount > 0 else f"突然大额净流出: {net_amount:,.0f}元",
                    'severity': 'high' if abs(net_amount) > 100000000 else 'medium',
                    'details': {
                        'net_amount': net_amount,
                        'threshold': self.anomaly_thresholds['sudden_large_inflow'],
                        'main_force_ratio': current_flow['main_force']['net_amount'] / (current_flow['main_force']['buy_amount'] + current_flow['main_force']['sell_amount']) if (current_flow['main_force']['buy_amount'] + current_flow['main_force']['sell_amount']) > 0 else 0
                    }
                }

    def _check_continuous_flow_anomaly(self, symbol, historical_flows):
        """检查连续资金流向异常"""
        if len(historical_flows) < 3:
            return None

        recent_flows = historical_flows[-5:]  # 最近5天
        consecutive_inflow = 0
        consecutive_outflow = 0

        for flow in recent_flows:
            net_amount = flow['main_force']['net_amount']
            if net_amount > 0:
                consecutive_inflow += 1
                consecutive_outflow = 0
            elif net_amount < 0:
                consecutive_outflow += 1
                consecutive_inflow = 0
            else:
                consecutive_inflow = 0
                consecutive_outflow = 0

        # 检查连续流入
        if consecutive_inflow >= self.anomaly_thresholds['continuous_inflow_days']:
            alert_key = f"continuous_inflow_{symbol}"
            if self._should_send_alert(alert_key):
                return {
                    'type': 'continuous_inflow',
                    'description': f"连续{consecutive_inflow}天净流入",
                    'severity': 'medium',
                    'details': {
                        'consecutive_days': consecutive_inflow,
                        'recent_average': sum(flow['main_force']['net_amount'] for flow in recent_flows) / len(recent_flows)
                    }
                }

        # 检查连续流出
        if consecutive_outflow >= self.anomaly_thresholds['continuous_outflow_days']:
            alert_key = f"continuous_outflow_{symbol}"
            if self._should_send_alert(alert_key):
                return {
                    'type': 'continuous_outflow',
                    'description': f"连续{consecutive_outflow}天净流出",
                    'severity': 'medium',
                    'details': {
                        'consecutive_days': consecutive_outflow,
                        'recent_average': sum(flow['main_force']['net_amount'] for flow in recent_flows) / len(recent_flows)
                    }
                }

    def _check_intensity_anomaly(self, symbol, current_flow, historical_flows):
        """检查资金流向强度异常"""
        if not historical_flows:
            return None

        current_intensity = current_flow['intensity']['overall_intensity']
        historical_intensities = [flow['intensity']['overall_intensity'] for flow in historical_flows[-5:]]

        if not historical_intensities:
            return None

        avg_historical_intensity = sum(historical_intensities) / len(historical_intensities)

        # 检查强度突增
        if avg_historical_intensity > 0 and current_intensity / avg_historical_intensity > self.anomaly_thresholds['intensity_spike']:
            alert_key = f"intensity_spike_{symbol}"
            if self._should_send_alert(alert_key):
                return {
                    'type': 'intensity_spike',
                    'description': f"资金流向强度突增: {current_intensity:.2f} (历史平均: {avg_historical_intensity:.2f})",
                    'severity': 'medium',
                    'details': {
                        'current_intensity': current_intensity,
                        'historical_average': avg_historical_intensity,
                        'spike_ratio': current_intensity / avg_historical_intensity,
                        'total_amount': current_flow['intensity']['total_amount']
                    }
                }

    def _should_send_alert(self, alert_key):
        """判断是否应该发送告警（考虑冷却时间）"""
        current_time = time.time()

        if alert_key in self.last_alerts:
            if current_time - self.last_alerts[alert_key] < self.alert_cooldown:
                return False

        self.last_alerts[alert_key] = current_time
        return True

    def generate_fund_flow_alert(self, symbol, anomalies):
        """生成资金流向告警"""
        for anomaly in anomalies:
            # 构建告警消息
            alert_message = f"""
            资金流向异常告警:
            股票代码: {symbol}
            异常类型: {anomaly['type']}
            异常描述: {anomaly['description']}
            严重程度: {anomaly['severity']}
            发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            详细信息:
            """

            if 'details' in anomaly:
                for key, value in anomaly['details'].items():
                    alert_message += f"  {key}: {value}\n"

            # 根据严重程度选择通知方式
            if anomaly['severity'] == 'high':
                self._send_alert(alert_message, ['email', 'webhook'])
            else:
                self._send_alert(alert_message, ['webhook'])

            # 记录告警
            self._log_alert(symbol, anomaly)
```

---

## 5. 实施监控和运维

### 5.1 实时监控仪表板设计

#### 关键指标监控配置
```yaml
monitoring_dashboard:
  real_time_metrics:
    - name: "接口响应时间"
      metric: "response_time"
      target: "< 3秒"
      warning_threshold: 5
      critical_threshold: 10
      unit: "秒"
      aggregation: "avg"

    - name: "数据更新延迟"
      metric: "update_delay"
      target: "< 5秒"
      warning_threshold: 15
      critical_threshold: 30
      unit: "秒"
      aggregation: "max"

    - name: "数据质量评分"
      metric: "data_quality_score"
      target: "> 90"
      warning_threshold: 85
      critical_threshold: 80
      unit: "分"
      aggregation: "min"

    - name: "接口可用性"
      metric: "interface_availability"
      target: "> 99.5%"
      warning_threshold: 99.0
      critical_threshold: 98.0
      unit: "%"
      aggregation: "avg"

  business_metrics:
    - name: "数据采集成功率"
      metric: "collection_success_rate"
      target: "> 99%"
      warning_threshold: 97
      critical_threshold: 95
      unit: "%"
      aggregation: "avg"

    - name: "异常数据检测率"
      metric: "anomaly_detection_rate"
      target: "> 95%"
      warning_threshold: 90
      critical_threshold: 85
      unit: "%"
      aggregation: "avg"

    - name: "数据完整性"
      metric: "data_completeness"
      target: "> 99%"
      warning_threshold: 95
      critical_threshold: 90
      unit: "%"
      aggregation: "min"
```

#### 监控系统实施
```python
class MonitoringSystem:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.dashboard = Dashboard()

        self.monitoring_config = self._load_monitoring_config()

    def start_monitoring(self):
        """启动监控系统"""
        logger.info("启动实时监控系统")

        # 启动指标收集
        metrics_thread = threading.Thread(target=self._collect_metrics_loop)
        metrics_thread.daemon = True
        metrics_thread.start()

        # 启动告警检查
        alert_thread = threading.Thread(target=self._check_alerts_loop)
        alert_thread.daemon = True
        alert_thread.start()

        # 启动仪表板更新
        dashboard_thread = threading.Thread(target=self._update_dashboard_loop)
        dashboard_thread.daemon = True
        dashboard_thread.start()

        logger.info("监控系统启动完成")

    def _collect_metrics_loop(self):
        """指标收集循环"""
        while True:
            try:
                # 收集实时指标
                metrics = self._collect_real_time_metrics()

                # 存储指标
                self.metrics_collector.store_metrics(metrics)

                # 等待下次收集
                time.sleep(30)  # 30秒收集一次

            except Exception as e:
                logger.error(f"指标收集失败: {e}")
                time.sleep(60)  # 错误时等待1分钟

    def _collect_real_time_metrics(self):
        """收集实时指标"""
        metrics = {}

        # 接口响应时间
        response_times = self._get_interface_response_times()
        metrics['response_time'] = {
            'avg': statistics.mean(response_times) if response_times else 0,
            'max': max(response_times) if response_times else 0,
            'min': min(response_times) if response_times else 0,
            'count': len(response_times)
        }

        # 数据质量评分
        quality_scores = self._get_data_quality_scores()
        metrics['data_quality_score'] = {
            'avg': statistics.mean(quality_scores) if quality_scores else 0,
            'min': min(quality_scores) if quality_scores else 0,
            'count': len(quality_scores)
        }

        # 接口可用性
        availability = self._get_interface_availability()
        metrics['interface_availability'] = availability

        # 数据采集成功率
        success_rate = self._get_collection_success_rate()
        metrics['collection_success_rate'] = success_rate

        # 数据更新延迟
        update_delays = self._get_update_delays()
        metrics['update_delay'] = {
            'avg': statistics.mean(update_delays) if update_delays else 0,
            'max': max(update_delays) if update_delays else 0,
            'count': len(update_delays)
        }

        return metrics

    def _check_alerts_loop(self):
        """告警检查循环"""
        while True:
            try:
                # 获取最新指标
                metrics = self.metrics_collector.get_latest_metrics()

                # 检查告警条件
                alerts = self._check_alert_conditions(metrics)

                # 发送告警
                for alert in alerts:
                    self.alert_manager.send_alert(alert)

                # 等待下次检查
                time.sleep(60)  # 1分钟检查一次

            except Exception as e:
                logger.error(f"告警检查失败: {e}")
                time.sleep(120)  # 错误时等待2分钟

    def _check_alert_conditions(self, metrics):
        """检查告警条件"""
        alerts = []

        for metric_config in self.monitoring_config['real_time_metrics']:
            metric_name = metric_config['metric']

            if metric_name in metrics:
                metric_value = metrics[metric_name]

                # 检查严重告警
                if isinstance(metric_value, dict):
                    value = metric_value.get('avg', 0)
                else:
                    value = metric_value

                # 检查严重阈值
                if 'critical_threshold' in metric_config:
                    critical_threshold = metric_config['critical_threshold']

                    if metric_config['unit'] == '%' or metric_config['unit'] == '分':
                        if value < critical_threshold:
                            alerts.append({
                                'metric': metric_name,
                                'severity': 'critical',
                                'value': value,
                                'threshold': critical_threshold,
                                'message': f"{metric_config['name']}严重异常: {value}{metric_config['unit']} (阈值: {critical_threshold}{metric_config['unit']})"
                            })
                    else:  # 数值型指标（如响应时间）
                        if value > critical_threshold:
                            alerts.append({
                                'metric': metric_name,
                                'severity': 'critical',
                                'value': value,
                                'threshold': critical_threshold,
                                'message': f"{metric_config['name']}严重异常: {value}{metric_config['unit']} (阈值: {critical_threshold}{metric_config['unit']})"
                            })

                # 检查警告阈值
                if 'warning_threshold' in metric_config:
                    warning_threshold = metric_config['warning_threshold']

                    if metric_config['unit'] == '%' or metric_config['unit'] == '分':
                        if value < warning_threshold:
                            alerts.append({
                                'metric': metric_name,
                                'severity': 'warning',
                                'value': value,
                                'threshold': warning_threshold,
                                'message': f"{metric_config['name']}警告: {value}{metric_config['unit']} (阈值: {warning_threshold}{metric_config['unit']})"
                            })
                    else:  # 数值型指标
                        if value > warning_threshold:
                            alerts.append({
                                'metric': metric_name,
                                'severity': 'warning',
                                'value': value,
                                'threshold': warning_threshold,
                                'message': f"{metric_config['name']}警告: {value}{metric_config['unit']} (阈值: {warning_threshold}{metric_config['unit']})"
                            })

        return alerts
```

### 5.2 告警策略实施

#### 分级告警处理
```python
class AlertManager:
    def __init__(self):
        self.notification_channels = {
            'email': EmailNotifier(),
            'sms': SmsNotifier(),
            'webhook': WebhookNotifier(),
            'slack': SlackNotifier()
        }

        self.alert_handlers = {
            'critical': self._handle_critical_alert,
            'warning': self._handle_warning_alert,
            'info': self._handle_info_alert
        }

        self.alert_cooldown = {
            'critical': 300,  # 5分钟
            'warning': 600,   # 10分钟
            'info': 1800      # 30分钟
        }

        self.last_alerts = {}  # 防止重复告警

    def send_alert(self, alert):
        """发送告警"""
        try:
            # 检查是否需要冷却
            if self._is_in_cooldown(alert):
                logger.info(f"告警在冷却期，跳过: {alert['message']}")
                return

            # 记录告警
            self._record_alert(alert)

            # 根据严重程度处理
            handler = self.alert_handlers.get(alert['severity'])
            if handler:
                handler(alert)

            # 更新冷却时间
            self._update_cooldown(alert)

        except Exception as e:
            logger.error(f"发送告警失败: {e}")

    def _handle_critical_alert(self, alert):
        """处理紧急告警"""
        logger.error(f"紧急告警: {alert['message']}")

        # 1. 立即通知运维人员
        notification_channels = ['email', 'sms', 'webhook']
        self._send_notifications(alert, notification_channels)

        # 2. 自动故障恢复
        if '接口' in alert['message']:
            self._auto_switch_interface(alert)

        if '数据质量' in alert['message']:
            self._auto_data_recovery(alert)

        # 3. 创建工单
        self._create_incident_ticket(alert)

        # 4. 执行应急预案
        self._execute_emergency_plan(alert)

    def _handle_warning_alert(self, alert):
        """处理警告告警"""
        logger.warning(f"警告告警: {alert['message']}")

        # 1. 记录警告信息
        self._log_warning(alert)

        # 2. 发送通知
        notification_channels = ['webhook', 'email']
        self._send_notifications(alert, notification_channels)

        # 3. 监控趋势变化
        self._monitor_trend(alert)

        # 4. 准备应急预案
        self._prepare_contingency_plan(alert)

    def _handle_info_alert(self, alert):
        """处理信息告警"""
        logger.info(f"信息告警: {alert['message']}")

        # 1. 记录信息
        self._log_info(alert)

        # 2. 发送通知（仅webhook）
        self._send_notifications(alert, ['webhook'])

    def _auto_switch_interface(self, alert):
        """自动切换接口"""
        try:
            # 确定需要切换的接口类型
            interface_type = self._determine_interface_type(alert)

            # 执行切换
            if interface_type == 'real_time':
                self._switch_real_time_interface()
            elif interface_type == 'historical':
                self._switch_historical_interface()
            elif interface_type == 'financial':
                self._switch_financial_interface()

            logger.info(f"自动切换接口: {interface_type}")

        except Exception as e:
            logger.error(f"自动切换接口失败: {e}")

    def _auto_data_recovery(self, alert):
        """自动数据恢复"""
        try:
            # 确定需要恢复的数据类型
            data_type = self._determine_data_type(alert)

            # 执行数据恢复
            if data_type == 'real_time':
                self._recover_real_time_data()
            elif data_type == 'historical':
                self._recover_historical_data()
            elif data_type == 'financial':
                self._recover_financial_data()

            logger.info(f"自动数据恢复: {data_type}")

        except Exception as e:
            logger.error(f"自动数据恢复失败: {e}")

    def _create_incident_ticket(self, alert):
        """创建工单"""
        try:
            ticket_data = {
                'title': f"数据采集系统告警: {alert['metric']}",
                'description': alert['message'],
                'severity': alert['severity'],
                'metric': alert['metric'],
                'value': alert['value'],
                'threshold': alert['threshold'],
                'created_at': datetime.now().isoformat(),
                'assigned_to': '运维团队',
                'category': '系统监控'
            }

            # 调用工单系统API
            ticket_id = self._call_ticketing_system_api(ticket_data)

            logger.info(f"创建工单成功: {ticket_id}")

        except Exception as e:
            logger.error(f"创建工单失败: {e}")
```

### 5.3 性能优化策略

#### 缓存策略实施
```python
class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

        self.cache_config = {
            'real_time_data': {
                'ttl': 60,      # 1分钟
                'key_prefix': 'rt:'
            },
            'historical_data': {
                'ttl': 3600,    # 1小时
                'key_prefix': 'hist:'
            },
            'financial_data': {
                'ttl': 86400,   # 24小时
                'key_prefix': 'fin:'
            },
            'fund_flow_data': {
                'ttl': 300,     # 5分钟
                'key_prefix': 'ff:'
            }
        }

    def get_cached_data(self, data_type, key):
        """获取缓存数据"""
        cache_key = f"{self.cache_config[data_type]['key_prefix']}{key}"

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"获取缓存数据失败: {e}")

        return None

    def set_cached_data(self, data_type, key, data):
        """设置缓存数据"""
        cache_key = f"{self.cache_config[data_type]['key_prefix']}{key}"
        ttl = self.cache_config[data_type]['ttl']

        try:
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.error(f"设置缓存数据失败: {e}")

    def invalidate_cache(self, data_type, pattern=None):
        """清除缓存"""
        try:
            if pattern:
                # 按模式清除
                cache_pattern = f"{self.cache_config[data_type]['key_prefix']}{pattern}*"
                keys = self.redis_client.keys(cache_pattern)
                if keys:
                    self.redis_client.delete(*keys)
            else:
                # 清除该类型的所有缓存
                cache_pattern = f"{self.cache_config[data_type]['key_prefix']}*"
                keys = self.redis_client.keys(cache_pattern)
                if keys:
                    self.redis_client.delete(*keys)

        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
```

## 结论

本详细实施指南提供了A股数据采集系统的完整技术实现方案，包括：

### 核心特色

1. **精细化实施**: 每个数据类型都有详细的技术实现
2. **质量控制**: 多层次的数据质量检查和修复机制
3. **智能监控**: 实时监控和智能告警系统
4. **高可用性**: 多重备份和自动故障恢复
5. **性能优化**: 缓存策略和批量处理优化

### 实施效果预期

- **数据采集成功率**: > 99%
- **数据质量评分**: > 90分
- **系统可用性**: > 99.9%
- **故障恢复时间**: < 5分钟
- **监控覆盖率**: 100%

通过本指南的实施，将建立一个专业级、高可靠性的A股数据采集系统，为各类金融应用提供高质量的数据支撑。