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
        Clean and standardize stock code format (Gate-3 Alignment)
        - Removes SH/SZ/BJ prefixes and suffixes
        - Removes dots
        - Pads to 6 digits
        """
        if not code:
            return ""

        # Remove spaces and convert to uppercase
        code = str(code).strip().upper()
        
        # Remove dots (e.g., 000001.SZ -> 000001SZ)
        code = code.replace(".", "")

        # Remove common prefixes/suffixes
        prefixes = ['SH', 'SZ', 'BJ']
        for p in prefixes:
            if code.startswith(p):
                code = code[len(p):]
            if code.endswith(p):
                code = code[:-len(p)]

        # Pad to 6 digits if it's mostly numeric
        # Some special codes might exist, but usually it's 6 digits
        if code.isdigit() and len(code) < 6:
            code = code.zfill(6)

        return code

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
