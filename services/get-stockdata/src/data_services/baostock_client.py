# -*- coding: utf-8 -*-
"""
Baostock Client
Provides a robust interface for Baostock data services.
Support singleton pattern and context management for login/logout.
"""

import logging
import threading
import pandas as pd
from typing import Optional, Dict, Any, List
import baostock as bs
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BaostockClient:
    """Singleton Client for Baostock"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BaostockClient, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
            
    def __init__(self):
        if self._initialized:
            return
            
        self._login_status = False
        self._initialized = True
        
    def login(self) -> bool:
        """Login to Baostock system"""
        try:
            lg = bs.login()
            if lg.error_code == '0':
                self._login_status = True
                logger.info(f"Baostock login success: {lg.error_msg}")
                return True
            else:
                logger.error(f"Baostock login failed: {lg.error_msg}")
                return False
        except Exception as e:
            logger.error(f"Baostock login exception: {e}")
            return False
            
    def logout(self):
        """Logout from system"""
        try:
            if self._login_status:
                bs.logout()
                self._login_status = False
                logger.info("Baostock logout success")
        except Exception as e:
            logger.warning(f"Baostock logout error: {e}")

    def _ensure_login(self) -> bool:
        """Ensure logged in constraint (Thread-safe)"""
        with self._lock:  # P0 Fix: Add lock protection for thread safety
            if not self._login_status:
                return self.login()
            return True

    def query_stock_industry(self) -> Optional[pd.DataFrame]:
        """Fetch industry classification data
        
        Returns DataFrame with columns: 
        [code, code_name, industry, industryClassification]
        """
        if not self._ensure_login():
            return None
            
        try:
            rs = bs.query_stock_industry()
            if rs.error_code != '0':
                logger.warning(f"query_stock_industry failed: {rs.error_msg}")
                return None
                
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
                
            if not data_list:
                return pd.DataFrame()
                
            return pd.DataFrame(data_list, columns=rs.fields)
            
        except Exception as e:
            logger.error(f"Error querying industry: {e}")
            return None

    def query_history_k_data_plus(self, 
                                code: str, 
                                fields: str,
                                start_date: str = None, 
                                end_date: str = None,
                                frequency: str = "d",
                                adjustflag: str = "3") -> Optional[pd.DataFrame]:
        """Fetch historical K-line data (including PE/PB metrics)"""
        
        if not self._ensure_login():
            return None
            
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        try:
            # Baostock format: sh.600000
            bs_code = code
            if not (code.startswith("sh.") or code.startswith("sz.")):
                # Auto-detect or assume? 
                # Better to let caller handle, but we can try simple heuristic
                if code.startswith("6"): bs_code = f"sh.{code}"
                elif code.startswith("0") or code.startswith("3"): bs_code = f"sz.{code}"
                elif code.startswith("4") or code.startswith("8"): bs_code = f"bj.{code}"

            rs = bs.query_history_k_data_plus(
                bs_code, fields, 
                start_date=start_date, end_date=end_date, 
                frequency=frequency, adjustflag=adjustflag
            )
            
            if rs.error_code != '0':
                logger.warning(f"query_history_k_data_plus failed for {code}: {rs.error_msg}")
                return None
                
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
                
            if not data_list:
                return pd.DataFrame()
                
            return pd.DataFrame(data_list, columns=rs.fields)
            
        except Exception as e:
            logger.error(f"Error querying k_data for {code}: {e}")
            return None

# Global Instance
baostock_client = BaostockClient()
