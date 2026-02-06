"""
Data validation and formatting utilities for stock data

Provides standardized data cleaning and DataFrame validation.
"""
import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class DataValidator:
    """Data validation and cleaning utilities"""

    @staticmethod
    def validate_quote_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and standardize quote DataFrame
        
        Args:
            df: Raw quote DataFrame
            
        Returns:
            Cleaned and validated DataFrame
        """
        if df.empty:
            return df

        # Required columns
        required_cols = ['code', 'price', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            logger.warning(f"Missing required columns: {missing_cols}")
            return pd.DataFrame()

        # Data type validation
        df = df.copy()
        df['code'] = df['code'].astype(str)
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

        # Drop rows with invalid data
        df = df.dropna(subset=['price', 'volume'])

        # Ensure timestamp exists
        if 'timestamp' not in df.columns:
            df['timestamp'] = datetime.now().isoformat()

        return df

    @staticmethod
    def validate_kline_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and standardize K-line DataFrame
        
        Args:
            df: Raw K-line DataFrame
            
        Returns:
            Cleaned and validated DataFrame
        """
        if df.empty:
            return df

        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            logger.warning(f"Missing K-line columns: {missing_cols}")
            return pd.DataFrame()

        df = df.copy()

        # Convert OHLCV to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Parse datetime
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')

        # Drop invalid rows
        df = df.dropna()

        # Sort by datetime
        df = df.sort_values('datetime').reset_index(drop=True)

        return df

    @staticmethod
    def clean_stock_code(code: str) -> str:
        """
        标准化为 TS 格式: 6位代码.市场 (如 600519.SH, 000001.SZ)
        
        对齐 Gate-3 标准，确保能正确匹配 ClickHouse 中的带后缀代码。
        """
        if not code:
            return ""

        code = str(code).upper().strip()
        
        # 1. 识别核心代码与市场
        market = None
        raw_code = code

        # 处理带点的格式 (000001.SZ)
        if '.' in code:
            parts = code.split('.')
            if len(parts[0]) == 6:
                raw_code, market = parts[0], parts[1]
            elif len(parts[-1]) == 6:
                raw_code, market = parts[-1], parts[0]
        
        # 处理前缀 (SH600519)
        elif code.startswith(('SH', 'SZ', 'BJ')):
            market = code[:2]
            raw_code = code[2:]
            
        # 处理后缀 (600519SH)
        elif code.endswith(('SH', 'SZ', 'BJ')):
            market = code[-2:]
            raw_code = code[:-2]

        # 清洗核心代码 (只保留数字)
        raw_code = "".join(filter(str.isdigit, raw_code))
        if len(raw_code) < 6:
            raw_code = raw_code.zfill(6)

        # 2. 推断市场 (如果不明确)
        if not market or market not in ['SH', 'SZ', 'BJ']:
            if raw_code.startswith(('6', '9', '5')):
                market = 'SH'
            elif raw_code.startswith(('0', '3', '1')):
                market = 'SZ'
            elif raw_code.startswith(('4', '8')):
                market = 'BJ'
            else:
                market = 'SH' # 默认
        
        return f"{raw_code}.{market}"

    @staticmethod
    def filter_trading_hours(df: pd.DataFrame,
                            datetime_col: str = 'datetime') -> pd.DataFrame:
        """
        Filter data to trading hours only (09:30-11:30, 13:00-15:00)
        
        Args:
            df: DataFrame with datetime column
            datetime_col: Name of datetime column
            
        Returns:
            Filtered DataFrame
        """
        if df.empty or datetime_col not in df.columns:
            return df

        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])

        # Extract time
        df['_time'] = df[datetime_col].dt.time

        # Morning session: 09:30 - 11:30
        morning_start = pd.to_datetime('09:30:00').time()
        morning_end = pd.to_datetime('11:30:00').time()

        # Afternoon session: 13:00 - 15:00
        afternoon_start = pd.to_datetime('13:00:00').time()
        afternoon_end = pd.to_datetime('15:00:00').time()

        # Filter
        mask = ((df['_time'] >= morning_start) & (df['_time'] <= morning_end)) | \
               ((df['_time'] >= afternoon_start) & (df['_time'] <= afternoon_end))

        result = df[mask].drop(columns=['_time'])

        logger.info(f"Filtered to trading hours: {len(result)}/{len(df)} rows")
        return result


# Convenience functions
def validate_quotes(df: pd.DataFrame) -> pd.DataFrame:
    """Shorthand for quote validation"""
    return DataValidator.validate_quote_dataframe(df)


def validate_klines(df: pd.DataFrame) -> pd.DataFrame:
    """Shorthand for K-line validation"""
    return DataValidator.validate_kline_dataframe(df)


def clean_codes(codes: list[str]) -> list[str]:
    """Clean a list of stock codes"""
    return [DataValidator.clean_stock_code(code) for code in codes]
