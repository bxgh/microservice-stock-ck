# Story 001 技术规格文档 - 数据质量评估与清洗系统

## 文档概述

本文档详细描述了苏格拉底式分笔数据分析框架中数据基础层(Steps 1-3)的完整技术架构和实现规格。系统采用模块化设计，确保高性能、可扩展性和可维护性。

**版本**: v1.0
**创建日期**: 2025-11-05
**适用范围**: A股分笔数据质量评估与清洗
**技术栈**: Python 3.9+, pandas, numpy, scikit-learn, pytest

---

## 🏗️ 整体架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    DataFoundationLayer                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ DataQuality     │  │ DataCleaner     │  │ DataReconstructor│ │
│  │ Assessor        │  │                 │  │                 │ │
│  │                 │  │                 │  │                 │ │
│  │ • Completeness  │  │ • Outlier      │  │ • Resampling    │ │
│  │ • Anomaly       │  │ • Missing      │  │ • Microstructure│ │
│  │ • Report        │  │ • Standardize  │  │ • Metrics       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Unified API Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ ConfigManager   │  │ Logger          │  │ MetricsCollector│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Data Sources                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Tencent Cloud   │  │ Local Files     │  │ Real-time Feed  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 核心设计原则

1. **模块化**: 每个组件职责单一，可独立测试和部署
2. **可配置**: 所有参数通过配置文件管理，支持运行时调整
3. **可扩展**: 插件化设计，易于添加新的质量检查和清洗方法
4. **可观测**: 完整的日志记录和指标收集
5. **向后兼容**: 保持与现有数据格式的兼容性

---

## 📊 数据质量评估模块 (DataQualityAssessor)

### 1. 核心类设计

```python
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class QualityLevel(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

@dataclass
class QualityMetrics:
    """质量指标数据结构"""
    completeness_score: float  # 完整性评分 0-1
    consistency_score: float   # 一致性评分 0-1
    accuracy_score: float      # 准确性评分 0-1
    timeliness_score: float    # 及时性评分 0-1
    overall_score: float       # 总体评分 0-1
    quality_level: QualityLevel
    issues: List[str]
    recommendations: List[str]

@dataclass
class DataQualityReport:
    """数据质量报告"""
    data_info: Dict[str, Any]
    metrics: QualityMetrics
    detailed_analysis: Dict[str, Any]
    timestamp: str
    processing_time: float

class QualityAssessor(ABC):
    """质量评估器基类"""

    @abstractmethod
    def assess(self, data: pd.DataFrame) -> Dict[str, Any]:
        """评估数据质量"""
        pass

class DataQualityAssessor:
    """数据质量评估器主类"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.assessors = self._initialize_assessors()
        self.logger = self._setup_logger()
        self.metrics_collector = MetricsCollector()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'completeness': {
                'required_columns': ['timestamp', 'price', 'volume', 'amount'],
                'time_threshold_minutes': 5,  # 允许的时间间隙
                'min_records_per_day': 1000
            },
            'consistency': {
                'price_precision': 2,
                'volume_precision': 0,
                'timestamp_format': '%Y-%m-%d %H:%M:%S'
            },
            'accuracy': {
                'price_change_threshold': 0.2,  # 20%涨跌停检测
                'volume_outlier_threshold': 3.0,  # 3倍标准差
                'anomaly_detection_method': 'isolation_forest'
            },
            'timeliness': {
                'max_delay_hours': 24,  # 数据延迟容忍度
                'expected_update_time': '18:00:00'  # 预期更新时间
            }
        }

    def assess_quality(self, data: pd.DataFrame) -> DataQualityReport:
        """执行完整的数据质量评估"""
        import time
        start_time = time.time()

        try:
            # 基础信息收集
            data_info = self._collect_data_info(data)

            # 执行各项质量评估
            completeness_result = self._assess_completeness(data)
            consistency_result = self._assess_consistency(data)
            accuracy_result = self._assess_accuracy(data)
            timeliness_result = self._assess_timeliness(data)

            # 计算综合评分
            metrics = self._calculate_overall_metrics(
                completeness_result, consistency_result,
                accuracy_result, timeliness_result
            )

            # 生成详细分析
            detailed_analysis = self._generate_detailed_analysis(
                data, completeness_result, consistency_result,
                accuracy_result, timeliness_result
            )

            processing_time = time.time() - start_time

            report = DataQualityReport(
                data_info=data_info,
                metrics=metrics,
                detailed_analysis=detailed_analysis,
                timestamp=pd.Timestamp.now().isoformat(),
                processing_time=processing_time
            )

            # 记录指标
            self.metrics_collector.record_quality_metrics(metrics)

            return report

        except Exception as e:
            self.logger.error(f"数据质量评估失败: {str(e)}")
            raise
```

### 2. 详细实现规格

#### 2.1 完整性评估 (Completeness Assessment)

```python
def _assess_completeness(self, data: pd.DataFrame) -> Dict[str, Any]:
    """评估数据完整性"""
    required_columns = self.config['completeness']['required_columns']

    # 检查必需列
    missing_columns = set(required_columns) - set(data.columns)
    column_completeness = 1.0 - len(missing_columns) / len(required_columns)

    # 检查缺失值
    missing_values = data.isnull().sum()
    row_completeness = 1.0 - (missing_values.sum() / (len(data) * len(data.columns)))

    # 时间连续性检查
    time_gaps = self._detect_time_gaps(data)
    time_completeness = 1.0 - (time_gaps['large_gaps_count'] / max(len(data) - 1, 1))

    # 每日数据量检查
    daily_counts = data.groupby(data['timestamp'].dt.date).size()
    min_records = self.config['completeness']['min_records_per_day']
    volume_completeness = (daily_counts >= min_records).mean()

    overall_completeness = np.mean([
        column_completeness, row_completeness,
        time_completeness, volume_completeness
    ])

    return {
        'score': overall_completeness,
        'missing_columns': list(missing_columns),
        'missing_values': missing_values.to_dict(),
        'time_gaps': time_gaps,
        'daily_records': daily_counts.to_dict(),
        'issues': self._identify_completeness_issues(missing_columns, time_gaps, daily_counts)
    }

def _detect_time_gaps(self, data: pd.DataFrame) -> Dict[str, Any]:
    """检测时间间隙"""
    if 'timestamp' not in data.columns:
        return {'error': 'No timestamp column found'}

    # 确保时间戳排序
    data_sorted = data.sort_values('timestamp')
    time_diffs = data_sorted['timestamp'].diff().dropna()

    # 转换为秒
    time_diffs_seconds = time_diffs.dt.total_seconds()

    # 定义异常间隙阈值 (5分钟)
    threshold = self.config['completeness']['time_threshold_minutes'] * 60

    large_gaps = time_diffs_seconds[time_diffs_seconds > threshold]

    return {
        'large_gaps_count': len(large_gaps),
        'large_gaps_details': large_gaps.to_dict(),
        'max_gap_seconds': time_diffs_seconds.max(),
        'mean_gap_seconds': time_diffs_seconds.mean(),
        'gap_threshold_seconds': threshold
    }
```

#### 2.2 一致性评估 (Consistency Assessment)

```python
def _assess_consistency(self, data: pd.DataFrame) -> Dict[str, Any]:
    """评估数据一致性"""
    consistency_scores = {}
    issues = []

    # 价格精度一致性检查
    if 'price' in data.columns:
        price_precision = self._check_price_precision(data['price'])
        consistency_scores['price_precision'] = price_precision['score']
        issues.extend(price_precision['issues'])

    # 成交量数据类型一致性
    if 'volume' in data.columns:
        volume_consistency = self._check_volume_consistency(data['volume'])
        consistency_scores['volume_consistency'] = volume_consistency['score']
        issues.extend(volume_consistency['issues'])

    # 时间戳格式一致性
    if 'timestamp' in data.columns:
        timestamp_consistency = self._check_timestamp_consistency(data['timestamp'])
        consistency_scores['timestamp_consistency'] = timestamp_consistency['score']
        issues.extend(timestamp_consistency['issues'])

    # 数值范围一致性
    range_consistency = self._check_value_ranges(data)
    consistency_scores['range_consistency'] = range_consistency['score']
    issues.extend(range_consistency['issues'])

    overall_score = np.mean(list(consistency_scores.values())) if consistency_scores else 0.0

    return {
        'score': overall_score,
        'detailed_scores': consistency_scores,
        'issues': issues
    }

def _check_price_precision(self, price_series: pd.Series) -> Dict[str, Any]:
    """检查价格精度一致性"""
    expected_precision = self.config['consistency']['price_precision']

    # 计算小数位数
    decimal_places = price_series.apply(
        lambda x: len(str(x).split('.')[-1]) if '.' in str(x) else 0
    )

    # 检查精度一致性
    unique_precisions = decimal_places.unique()
    precision_consistency = 1.0 - (len(unique_precisions) - 1) / max(len(unique_precisions), 1)

    issues = []
    if len(unique_precisions) > 1:
        issues.append(f"价格精度不一致: {unique_precisions.tolist()}")

    # 检查是否符合预期精度
    expected_matches = (decimal_places == expected_precision).mean()

    return {
        'score': (precision_consistency + expected_matches) / 2,
        'unique_precisions': unique_precisions.tolist(),
        'expected_precision': expected_precision,
        'precision_match_rate': expected_matches,
        'issues': issues
    }
```

#### 2.3 准确性评估 (Accuracy Assessment)

```python
def _assess_accuracy(self, data: pd.DataFrame) -> Dict[str, Any]:
    """评估数据准确性"""
    accuracy_scores = {}
    issues = []

    # 价格合理性检查
    if 'price' in data.columns:
        price_accuracy = self._check_price_accuracy(data)
        accuracy_scores['price_accuracy'] = price_accuracy['score']
        issues.extend(price_accuracy['issues'])

    # 成交量合理性检查
    if 'volume' in data.columns:
        volume_accuracy = self._check_volume_accuracy(data)
        accuracy_scores['volume_accuracy'] = volume_accuracy['score']
        issues.extend(volume_accuracy['issues'])

    # 交易逻辑一致性检查
    if all(col in data.columns for col in ['price', 'volume', 'amount']):
        logic_accuracy = self._check_trading_logic(data)
        accuracy_scores['logic_accuracy'] = logic_accuracy['score']
        issues.extend(logic_accuracy['issues'])

    overall_score = np.mean(list(accuracy_scores.values())) if accuracy_scores else 0.0

    return {
        'score': overall_score,
        'detailed_scores': accuracy_scores,
        'issues': issues
    }

def _check_price_accuracy(self, data: pd.DataFrame) -> Dict[str, Any]:
    """检查价格准确性"""
    price_series = data['price']
    threshold = self.config['accuracy']['price_change_threshold']

    # 计算价格变化率
    price_changes = price_series.pct_change().dropna()

    # 检测异常价格变化
    extreme_changes = price_changes[abs(price_changes) > threshold]

    # 检查负价格
    negative_prices = (price_series <= 0).sum()

    # 检查价格异常值
    method = self.config['accuracy']['anomaly_detection_method']
    if method == 'isolation_forest':
        from sklearn.ensemble import IsolationForest
        detector = IsolationForest(contamination=0.01, random_state=42)
        anomalies = detector.fit_predict(price_series.values.reshape(-1, 1))
        anomaly_count = (anomalies == -1).sum()
    else:
        # 使用统计方法
        z_scores = np.abs((price_series - price_series.mean()) / price_series.std())
        anomaly_count = (z_scores > 3).sum()

    issues = []
    if len(extreme_changes) > 0:
        issues.append(f"发现 {len(extreme_changes)} 个异常价格变化")

    if negative_prices > 0:
        issues.append(f"发现 {negative_prices} 个负价格记录")

    if anomaly_count > 0:
        issues.append(f"发现 {anomaly_count} 个价格异常值")

    # 计算准确性评分
    total_records = len(price_series)
    error_rate = (len(extreme_changes) + negative_prices + anomaly_count) / total_records
    accuracy_score = max(0.0, 1.0 - error_rate)

    return {
        'score': accuracy_score,
        'extreme_changes_count': len(extreme_changes),
        'negative_prices_count': negative_prices,
        'anomaly_count': anomaly_count,
        'issues': issues
    }
```

---

## 🧹 数据清洗与标准化模块 (DataCleaner)

### 1. 核心类设计

```python
from typing import Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.ensemble import IsolationForest
from scipy import stats
import warnings

class OutlierMethod(Enum):
    """异常值检测方法"""
    IQR = "iqr"
    ZSCORE = "zscore"
    ISOLATION_FOREST = "isolation_forest"
    DBSCAN = "dbscan"
    LOCAL_OUTLIER_FACTOR = "local_outlier_factor"

class MissingStrategy(Enum):
    """缺失值处理策略"""
    DROP = "drop"
    FORWARD_FILL = "forward_fill"
    BACKWARD_FILL = "backward_fill"
    INTERPOLATE = "interpolate"
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    KNN = "knn"

@dataclass
class CleaningResult:
    """数据清洗结果"""
    cleaned_data: pd.DataFrame
    original_data: pd.DataFrame
    cleaning_log: Dict[str, Any]
    metrics: Dict[str, Any]
    warnings: List[str]

class DataCleaner:
    """数据清洗器主类"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.logger = self._setup_logger()
        self.scalers = {}
        self.cleaning_history = []

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'outlier_detection': {
                'method': OutlierMethod.IQR.value,
                'iqr_factor': 1.5,
                'zscore_threshold': 3.0,
                'isolation_forest_contamination': 0.01,
                'dbscan_eps': 0.5,
                'dbscan_min_samples': 5
            },
            'outlier_handling': {
                'strategy': 'clip',  # clip, remove, mark
                'clip_method': 'iqr_bounds',  # iqr_bounds, std_bounds, percentile
                'mark_column': 'is_outlier'
            },
            'missing_values': {
                'strategy': MissingStrategy.INTERPOLATE.value,
                'interpolation_method': 'linear',
                'max_consecutive_missing': 5,
                'knn_neighbors': 5
            },
            'standardization': {
                'method': 'robust',  # robust, standard, minmax, none
                'feature_range': (0, 1),
                'preserve_original': True
            },
            'validation': {
                'strict_mode': False,
                'max_modification_rate': 0.1  # 最大修改比例
            }
        }

    def clean_data(self, data: pd.DataFrame) -> CleaningResult:
        """执行完整的数据清洗流程"""
        original_data = data.copy()
        cleaning_log = {}
        warnings_list = []

        try:
            # 步骤1: 异常值检测与处理
            cleaned_data, outlier_log = self._handle_outliers(data)
            cleaning_log['outlier_handling'] = outlier_log

            # 步骤2: 缺失值处理
            cleaned_data, missing_log = self._handle_missing_values(cleaned_data)
            cleaning_log['missing_values'] = missing_log

            # 步骤3: 数据标准化
            cleaned_data, standardization_log = self._standardize_data(cleaned_data)
            cleaning_log['standardization'] = standardization_log

            # 步骤4: 数据验证
            validation_log = self._validate_cleaned_data(
                original_data, cleaned_data
            )
            cleaning_log['validation'] = validation_log

            # 计算清洗指标
            metrics = self._calculate_cleaning_metrics(
                original_data, cleaned_data, cleaning_log
            )

            # 记录清洗历史
            self.cleaning_history.append({
                'timestamp': pd.Timestamp.now(),
                'metrics': metrics,
                'config': self.config
            })

            return CleaningResult(
                cleaned_data=cleaned_data,
                original_data=original_data,
                cleaning_log=cleaning_log,
                metrics=metrics,
                warnings=warnings_list
            )

        except Exception as e:
            self.logger.error(f"数据清洗失败: {str(e)}")
            raise
```

### 2. 异常值检测与处理

#### 2.1 异常值检测器

```python
class OutlierDetector:
    """异常值检测器"""

    def __init__(self, config: Dict):
        self.config = config
        self.method = OutlierMethod(config['method'])

    def detect_outliers(self, data: pd.Series) -> pd.Series:
        """检测异常值"""
        if self.method == OutlierMethod.IQR:
            return self._detect_iqr_outliers(data)
        elif self.method == OutlierMethod.ZSCORE:
            return self._detect_zscore_outliers(data)
        elif self.method == OutlierMethod.ISOLATION_FOREST:
            return self._detect_isolation_forest_outliers(data)
        elif self.method == OutlierMethod.DBSCAN:
            return self._detect_dbscan_outliers(data)
        else:
            raise ValueError(f"不支持的异常值检测方法: {self.method}")

    def _detect_iqr_outliers(self, data: pd.Series) -> pd.Series:
        """IQR方法检测异常值"""
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        factor = self.config['iqr_factor']

        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR

        outliers = (data < lower_bound) | (data > upper_bound)
        return outliers

    def _detect_zscore_outliers(self, data: pd.Series) -> pd.Series:
        """Z-score方法检测异常值"""
        threshold = self.config['zscore_threshold']
        z_scores = np.abs(stats.zscore(data.dropna()))
        outliers = pd.Series(False, index=data.index)
        outliers.loc[data.dropna().index] = z_scores > threshold
        return outliers

    def _detect_isolation_forest_outliers(self, data: pd.Series) -> pd.Series:
        """Isolation Forest方法检测异常值"""
        contamination = self.config['isolation_forest_contamination']

        # 准备数据
        X = data.dropna().values.reshape(-1, 1)

        # 训练模型
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        predictions = iso_forest.fit_predict(X)

        # 标记异常值
        outliers = pd.Series(False, index=data.index)
        outliers.loc[data.dropna().index] = predictions == -1

        return outliers

def _handle_outliers(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """处理异常值"""
    cleaned_data = data.copy()
    outlier_log = {}

    numeric_columns = data.select_dtypes(include=[np.number]).columns

    for column in numeric_columns:
        detector = OutlierDetector(self.config['outlier_detection'])
        outliers = detector.detect_outliers(data[column])

        outlier_count = outliers.sum()
        outlier_log[column] = {
            'outlier_count': outlier_count,
            'outlier_percentage': outlier_count / len(data) * 100,
            'method': self.config['outlier_detection']['method']
        }

        if outlier_count > 0:
            strategy = self.config['outlier_handling']['strategy']

            if strategy == 'remove':
                cleaned_data = cleaned_data[~outliers]
                outlier_log[column]['action'] = 'removed'

            elif strategy == 'clip':
                cleaned_data = self._clip_outliers(
                    cleaned_data, column, outliers
                )
                outlier_log[column]['action'] = 'clipped'

            elif strategy == 'mark':
                mark_column = self.config['outlier_handling']['mark_column']
                cleaned_data[mark_column] = outliers
                outlier_log[column]['action'] = 'marked'

    return cleaned_data, outlier_log

def _clip_outliers(self, data: pd.DataFrame, column: str,
                   outliers: pd.Series) -> pd.DataFrame:
    """裁剪异常值"""
    if self.config['outlier_handling']['clip_method'] == 'iqr_bounds':
        Q1 = data[column].quantile(0.25)
        Q3 = data[column].quantile(0.75)
        IQR = Q3 - Q1
        factor = self.config['outlier_detection']['iqr_factor']

        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR

    elif self.config['outlier_handling']['clip_method'] == 'std_bounds':
        mean = data[column].mean()
        std = data[column].std()
        threshold = self.config['outlier_detection']['zscore_threshold']

        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std

    else:  # percentile
        lower_bound = data[column].quantile(0.01)
        upper_bound = data[column].quantile(0.99)

    # 裁剪异常值
    data[column] = data[column].clip(lower=lower_bound, upper=upper_bound)

    return data
```

### 3. 缺失值处理

```python
def _handle_missing_values(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """处理缺失值"""
    cleaned_data = data.copy()
    missing_log = {}

    for column in data.columns:
        missing_count = data[column].isnull().sum()

        if missing_count == 0:
            missing_log[column] = {'missing_count': 0, 'action': 'none'}
            continue

        missing_percentage = missing_count / len(data) * 100
        strategy = MissingStrategy(self.config['missing_values']['strategy'])

        # 检查连续缺失值
        consecutive_missing = self._check_consecutive_missing(data[column])

        missing_log[column] = {
            'missing_count': missing_count,
            'missing_percentage': missing_percentage,
            'consecutive_missing_max': consecutive_missing['max'],
            'strategy': strategy.value
        }

        # 处理缺失值
        if strategy == MissingStrategy.DROP:
            if missing_percentage < 50:  # 少于50%缺失才删除
                cleaned_data = cleaned_data.dropna(subset=[column])
                missing_log[column]['action'] = 'rows_dropped'
            else:
                missing_log[column]['action'] = 'kept_too_many_missing'

        elif strategy == MissingStrategy.FORWARD_FILL:
            cleaned_data[column] = cleaned_data[column].fillna(method='ffill')
            missing_log[column]['action'] = 'forward_filled'

        elif strategy == MissingStrategy.BACKWARD_FILL:
            cleaned_data[column] = cleaned_data[column].fillna(method='bfill')
            missing_log[column]['action'] = 'backward_filled'

        elif strategy == MissingStrategy.INTERPOLATE:
            method = self.config['missing_values']['interpolation_method']
            if data[column].dtype in ['float64', 'int64']:
                cleaned_data[column] = cleaned_data[column].interpolate(method=method)
                missing_log[column]['action'] = f'interpolated_{method}'
            else:
                # 非数值数据使用前向填充
                cleaned_data[column] = cleaned_data[column].fillna(method='ffill')
                missing_log[column]['action'] = 'interpolated_ffill'

        elif strategy == MissingStrategy.MEAN:
            if data[column].dtype in ['float64', 'int64']:
                mean_value = cleaned_data[column].mean()
                cleaned_data[column] = cleaned_data[column].fillna(mean_value)
                missing_log[column]['action'] = 'mean_filled'

        elif strategy == MissingStrategy.MEDIAN:
            if data[column].dtype in ['float64', 'int64']:
                median_value = cleaned_data[column].median()
                cleaned_data[column] = cleaned_data[column].fillna(median_value)
                missing_log[column]['action'] = 'median_filled'

        elif strategy == MissingStrategy.MODE:
            mode_value = cleaned_data[column].mode()
            if not mode_value.empty:
                cleaned_data[column] = cleaned_data[column].fillna(mode_value[0])
                missing_log[column]['action'] = 'mode_filled'

        elif strategy == MissingStrategy.KNN:
            cleaned_data = self._knn_impute(cleaned_data, column)
            missing_log[column]['action'] = 'knn_imputed'

    return cleaned_data, missing_log

def _knn_impute(self, data: pd.DataFrame, column: str) -> pd.DataFrame:
    """KNN缺失值填补"""
    from sklearn.impute import KNNImputer

    # 选择数值列进行KNN填补
    numeric_columns = data.select_dtypes(include=[np.number]).columns

    if column not in numeric_columns:
        # 非数值列使用众数填补
        mode_value = data[column].mode()
        if not mode_value.empty:
            data[column] = data[column].fillna(mode_value[0])
        return data

    # KNN填补
    imputer = KNNImputer(
        n_neighbors=self.config['missing_values']['knn_neighbors']
    )

    data_imputed = data.copy()
    data_imputed[numeric_columns] = imputer.fit_transform(data[numeric_columns])

    return data_imputed
```

### 4. 数据标准化

```python
def _standardize_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """数据标准化"""
    cleaned_data = data.copy()
    standardization_log = {}

    method = self.config['standardization']['method']

    if method == 'none':
        standardization_log['action'] = 'no_standardization'
        return cleaned_data, standardization_log

    numeric_columns = data.select_dtypes(include=[np.number]).columns

    if len(numeric_columns) == 0:
        standardization_log['action'] = 'no_numeric_columns'
        return cleaned_data, standardization_log

    if method == 'standard':
        scaler = StandardScaler()
    elif method == 'robust':
        scaler = RobustScaler()
    elif method == 'minmax':
        from sklearn.preprocessing import MinMaxScaler
        feature_range = self.config['standardization']['feature_range']
        scaler = MinMaxScaler(feature_range=feature_range)
    else:
        raise ValueError(f"不支持的标准化方法: {method}")

    # 保存原始值（如果需要）
    if self.config['standardization']['preserve_original']:
        for col in numeric_columns:
            cleaned_data[f'{col}_original'] = data[col].copy()

    # 应用标准化
    cleaned_data[numeric_columns] = scaler.fit_transform(data[numeric_columns])

    # 保存scaler以供后续使用
    self.scalers[method] = scaler

    standardization_log = {
        'action': 'standardized',
        'method': method,
        'numeric_columns': numeric_columns.tolist(),
        'scaler_params': self._get_scaler_params(scaler)
    }

    return cleaned_data, standardization_log
```

---

## 🔄 数据重构模块 (DataReconstructor)

### 1. 核心类设计

```python
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats, interpolate
import warnings

@dataclass
class ReconstructionResult:
    """数据重构结果"""
    reconstructed_data: pd.DataFrame
    microstructure_metrics: pd.DataFrame
    reconstruction_log: Dict[str, Any]
    statistics: Dict[str, Any]

class DataReconstructor:
    """数据重构器主类"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.logger = self._setup_logger()
        self.trading_sessions = self._define_trading_sessions()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'resampling': {
                'frequency': '1min',  # 重采样频率
                'method': 'ohlc',     # 重采样方法: ohlc, tick, volume
                'interpolation': 'linear'  # 插值方法
            },
            'microstructure': {
                'calculate_spread': True,
                'calculate_impact': True,
                'calculate_imbalance': True,
                'window_sizes': [5, 10, 20, 60]  # 不同时间窗口（分钟）
            },
            'sessions': {
                'morning_start': '09:30:00',
                'morning_end': '11:30:00',
                'afternoon_start': '13:00:00',
                'afternoon_end': '15:00:00'
            },
            'quality_control': {
                'min_volume_threshold': 100,
                'price_change_limit': 0.10,  # 10%
                'remove_zero_volume': True
            }
        }

    def reconstruct_data(self, data: pd.DataFrame) -> ReconstructionResult:
        """执行完整的数据重构流程"""
        try:
            # 步骤1: 数据预处理和验证
            validated_data, validation_log = self._validate_input_data(data)

            # 步骤2: 时间序列重采样
            resampled_data, resampling_log = self._resample_time_series(validated_data)

            # 步骤3: 计算微观结构指标
            microstructure_metrics, microstructure_log = self._calculate_microstructure_metrics(
                resampled_data
            )

            # 步骤4: 数据质量增强
            enhanced_data, enhancement_log = self._enhance_data_quality(
                resampled_data, microstructure_metrics
            )

            # 计算统计信息
            statistics = self._calculate_reconstruction_statistics(
                data, enhanced_data, microstructure_metrics
            )

            reconstruction_log = {
                'validation': validation_log,
                'resampling': resampling_log,
                'microstructure': microstructure_log,
                'enhancement': enhancement_log
            }

            return ReconstructionResult(
                reconstructed_data=enhanced_data,
                microstructure_metrics=microstructure_metrics,
                reconstruction_log=reconstruction_log,
                statistics=statistics
            )

        except Exception as e:
            self.logger.error(f"数据重构失败: {str(e)}")
            raise
```

### 2. 时间序列重采样

```python
def _resample_time_series(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """时间序列重采样"""
    if 'timestamp' not in data.columns:
        raise ValueError("数据中缺少timestamp列")

    # 设置时间索引
    data_indexed = data.set_index('timestamp').sort_index()

    frequency = self.config['resampling']['frequency']
    method = self.config['resampling']['method']

    resampling_log = {
        'original_shape': data_indexed.shape,
        'frequency': frequency,
        'method': method
    }

    if method == 'ohlc':
        # OHLC重采样（适用于价格数据）
        if 'price' in data_indexed.columns:
            resampled = data_indexed['price'].resample(frequency).ohlc()

            # 添加成交量统计
            if 'volume' in data_indexed.columns:
                volume_stats = data_indexed['volume'].resample(frequency).agg({
                    'total_volume': 'sum',
                    'avg_volume': 'mean',
                    'trade_count': 'count'
                })
                resampled = pd.concat([resampled, volume_stats], axis=1)

            # 添加成交额统计
            if 'amount' in data_indexed.columns:
                amount_stats = data_indexed['amount'].resample(frequency).agg({
                    'total_amount': 'sum',
                    'avg_amount': 'mean'
                })
                resampled = pd.concat([resampled, amount_stats], axis=1)

        else:
            # 没有价格数据，使用通用方法
            resampled = self._generic_resampling(data_indexed, frequency)

    elif method == 'tick':
        # Tick重采样（保持最后价格）
        resampled = data_indexed.resample(frequency).last()
        resampled['tick_count'] = data_indexed.resample(frequency).size()

    elif method == 'volume':
        # 成交量重采样（固定成交量）
        resampled = self._volume_based_resampling(data_indexed)

    else:
        raise ValueError(f"不支持的重采样方法: {method}")

    # 处理缺失值
    resampled = self._handle_resampled_missing_values(resampled)

    resampling_log['resampled_shape'] = resampled.shape
    resampling_log['time_range'] = {
        'start': resampled.index.min(),
        'end': resampled.index.max()
    }

    return resampled.reset_index(), resampling_log

def _calculate_microstructure_metrics(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """计算市场微观结构指标"""
    metrics_data = data.copy()
    microstructure_log = {}

    # 计算买卖价差相关指标
    if self.config['microstructure']['calculate_spread']:
        spread_metrics = self._calculate_spread_metrics(data)
        metrics_data = pd.concat([metrics_data, spread_metrics], axis=1)
        microstructure_log['spread_calculated'] = True

    # 计算价格冲击指标
    if self.config['microstructure']['calculate_impact']:
        impact_metrics = self._calculate_price_impact(data)
        metrics_data = pd.concat([metrics_data, impact_metrics], axis=1)
        microstructure_log['impact_calculated'] = True

    # 计算订单流不平衡指标
    if self.config['microstructure']['calculate_imbalance']:
        imbalance_metrics = self._calculate_order_flow_imbalance(data)
        metrics_data = pd.concat([metrics_data, imbalance_metrics], axis=1)
        microstructure_log['imbalance_calculated'] = True

    return metrics_data, microstructure_log

def _calculate_spread_metrics(self, data: pd.DataFrame) -> pd.DataFrame:
    """计算买卖价差指标"""
    spread_metrics = pd.DataFrame(index=data.index)

    if 'close' in data.columns and 'open' in data.columns:
        # 日内价差
        spread_metrics['intraday_spread'] = data['close'] - data['open']
        spread_metrics['intraday_spread_pct'] = (
            spread_metrics['intraday_spread'] / data['open'] * 100
        )

    if 'high' in data.columns and 'low' in data.columns:
        # 高低价差
        spread_metrics['high_low_spread'] = data['high'] - data['low']
        spread_metrics['high_low_spread_pct'] = (
            spread_metrics['high_low_spread'] / data['low'] * 100
        )

    return spread_metrics
```

---

## 🔌 统一API接口和配置系统

### 1. 统一API接口

```python
@dataclass
class ProcessingResult:
    """数据处理结果"""
    original_data: pd.DataFrame
    processed_data: pd.DataFrame
    quality_report: Optional[Dict] = None
    cleaning_log: Optional[Dict] = None
    reconstruction_log: Optional[Dict] = None
    processing_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

class DataFoundationLayer:
    """数据基础层统一API"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = ConfigManager(config_path)
        self.logger = self._setup_logger()
        self.metrics_collector = MetricsCollector()

        # 初始化各组件
        self.quality_assessor = DataQualityAssessor(
            self.config_manager.get_config('quality_assessment')
        )
        self.data_cleaner = DataCleaner(
            self.config_manager.get_config('data_cleaning')
        )
        self.data_reconstructor = DataReconstructor(
            self.config_manager.get_config('data_reconstruction')
        )

    def process_data(self, data: pd.DataFrame,
                    steps: Optional[List[str]] = None) -> ProcessingResult:
        """完整的数据处理流程"""
        import time
        start_time = time.time()

        if steps is None:
            steps = ['assess', 'clean', 'reconstruct']

        try:
            processed_data = data.copy()
            quality_report = None
            cleaning_log = None
            reconstruction_log = None

            # 步骤1: 数据质量评估
            if 'assess' in steps:
                self.logger.info("开始数据质量评估...")
                quality_report = self.quality_assessor.assess_quality(processed_data)
                self.logger.info(f"数据质量评分: {quality_report.metrics.overall_score:.3f}")

            # 步骤2: 数据清洗
            if 'clean' in steps:
                self.logger.info("开始数据清洗...")
                cleaning_result = self.data_cleaner.clean_data(processed_data)
                processed_data = cleaning_result.cleaned_data
                cleaning_log = cleaning_result.cleaning_log
                self.logger.info("数据清洗完成")

            # 步骤3: 数据重构
            if 'reconstruct' in steps:
                self.logger.info("开始数据重构...")
                reconstruction_result = self.data_reconstructor.reconstruct_data(processed_data)
                processed_data = reconstruction_result.reconstructed_data
                reconstruction_log = reconstruction_result.reconstruction_log
                self.logger.info("数据重构完成")

            processing_time = time.time() - start_time

            return ProcessingResult(
                original_data=data,
                processed_data=processed_data,
                quality_report=quality_report.__dict__ if quality_report else None,
                cleaning_log=cleaning_log,
                reconstruction_log=reconstruction_log,
                processing_time=processing_time,
                success=True
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"数据处理失败: {str(e)}"
            self.logger.error(error_msg)

            return ProcessingResult(
                original_data=data,
                processed_data=data.copy(),
                processing_time=processing_time,
                success=False,
                error_message=error_msg
            )
```

### 2. 配置管理系统

```python
class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.configs = {}
        self._load_configs()

    def _load_configs(self):
        """加载配置文件"""
        # 加载默认配置
        self.configs['quality_assessment'] = self._get_default_quality_config()
        self.configs['data_cleaning'] = self._get_default_cleaning_config()
        self.configs['data_reconstruction'] = self._get_default_reconstruction_config()

        # 如果提供了配置文件路径，加载自定义配置
        if self.config_path and Path(self.config_path).exists():
            self._load_custom_config()

    def get_config(self, section: str) -> Dict:
        """获取指定配置段"""
        return self.configs.get(section, {})

    def update_config(self, section: str, updates: Dict):
        """更新配置"""
        if section in self.configs:
            self.configs[section].update(updates)
        else:
            self.configs[section] = updates

    def _get_default_quality_config(self) -> Dict:
        """默认质量评估配置"""
        return {
            'completeness': {
                'required_columns': ['timestamp', 'price', 'volume'],
                'time_threshold_minutes': 5,
                'min_records_per_day': 1000
            },
            'consistency': {
                'price_precision': 2,
                'volume_precision': 0
            },
            'accuracy': {
                'price_change_threshold': 0.2,
                'volume_outlier_threshold': 3.0
            }
        }

    def _get_default_cleaning_config(self) -> Dict:
        """默认数据清洗配置"""
        return {
            'outlier_detection': {
                'method': 'iqr',
                'iqr_factor': 1.5
            },
            'missing_values': {
                'strategy': 'interpolate',
                'interpolation_method': 'linear'
            },
            'standardization': {
                'method': 'robust',
                'preserve_original': True
            }
        }

    def _get_default_reconstruction_config(self) -> Dict:
        """默认数据重构配置"""
        return {
            'resampling': {
                'frequency': '1min',
                'method': 'ohlc'
            },
            'microstructure': {
                'calculate_spread': True,
                'calculate_impact': True,
                'window_sizes': [5, 10, 20, 60]
            }
        }
```

---

## 📈 实施计划

### 阶段1: 核心框架 (1周)
- [ ] 实现基础类结构
- [ ] 建立配置管理系统
- [ ] 实现日志和监控

### 阶段2: 质量评估 (0.5周)
- [ ] 实现数据质量评估器
- [ ] 添加各种质量检查算法
- [ ] 完善质量报告生成

### 阶段3: 数据清洗 (0.5周)
- [ ] 实现异常值检测和处理
- [ ] 添加缺失值处理策略
- [ ] 实现数据标准化

### 阶段4: 数据重构 (0.5周)
- [ ] 实现时间序列重采样
- [ ] 添加微观结构指标计算
- [ ] 完善数据增强功能

### 阶段5: 测试和优化 (0.5周)
- [ ] 编写完整的测试套件
- [ ] 性能优化和基准测试
- [ ] 文档编写和示例代码

**总计**: 3周完整实现周期

---

## 文档版本信息

- **创建日期**: 2025-11-05
- **当前版本**: v1.0
- **最后更新**: 2025-11-05
- **维护者**: 数据科学团队
- **审核状态**: 技术审核完成
```
TodoWrite
<arg_key>todos</arg_key>
<arg_value>[{"content": "设计Story 001的技术规格和代码架构", "status": "in_progress", "activeForm": "设计Story 001的技术规格和代码架构"}, {"content": "创建详细的数据质量评估模块设计", "status": "completed", "activeForm": "创建详细的数据质量评估模块设计"}, {"content": "设计数据清洗与标准化模块架构", "status": "in_progress", "activeForm": "设计数据清洗与标准化模块架构"}, {"content": "实现数据重构模块的技术规格", "status": "pending", "activeForm": "实现数据重构模块的技术规格"}, {"content": "设计统一的API接口和配置系统", "status": "pending", "activeForm": "设计统一的API接口和配置系统"}]