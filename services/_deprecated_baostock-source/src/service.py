import grpc
import logging
import json
import pandas as pd
import baostock as bs
from concurrent import futures
import time

from datasource.v1 import data_source_pb2
from datasource.v1 import data_source_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("baostock-service")

class BaostockService(data_source_pb2_grpc.DataSourceServiceServicer):
    def __init__(self):
        self.is_logged_in = False
        self._login()
        
    def _login(self):
        """Perform baostock login"""
        try:
            lg = bs.login()
            if lg.error_code == '0':
                self.is_logged_in = True
                logger.info(f"Baostock login success: {lg.error_msg}")
            else:
                self.is_logged_in = False
                logger.error(f"Baostock login failed: {lg.error_code} - {lg.error_msg}")
        except Exception as e:
            self.is_logged_in = False
            logger.error(f"Baostock login exception: {str(e)}")

    def HealthCheck(self, request, context):
        """Custom health check for Baostock"""
        # Auto-relogin if needed
        if not self.is_logged_in:
            logger.warning("Session expired, attempting re-login during health check")
            self._login()
            
        return data_source_pb2.HealthCheckResponse(
            healthy=self.is_logged_in,
            message="Baostock logged in" if self.is_logged_in else "Baostock login failed"
        )

    def GetCapabilities(self, request, context):
        """Return supported data types"""
        return data_source_pb2.CapabilitiesResponse(
            supported_types=[
                data_source_pb2.DATA_TYPE_HISTORY,
                data_source_pb2.DATA_TYPE_INDEX_DAILY
            ],
            priority=50  # Lower priority than AkShare/Mootdx
        )

    def FetchData(self, request, context):
        """Fetch data from Baostock"""
        if not self.is_logged_in:
            self._login()
            if not self.is_logged_in:
                return data_source_pb2.DataResponse(
                    success=False,
                    error_message="Baostock service not logged in"
                )

        try:
            params = dict(request.params)
            
            # Dispatch based on type
            if request.type == data_source_pb2.DATA_TYPE_HISTORY:
                return self._fetch_history(params)
                
            return data_source_pb2.DataResponse(
                success=False,
                error_message=f"Unsupported data type: {request.type}"
            )
            
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return data_source_pb2.DataResponse(
                success=False,
                error_message=str(e)
            )
            
    def _fetch_history(self, params):
        code = params.get('code')
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        adjust = params.get('adjust', 'qfq')  # Default to qfq
        
        # Baostock format: "sh.600000"
        if not code.startswith(('sh.', 'sz.')):
            if code.startswith('6'):
                bs_code = f"sh.{code}"
            else:
                bs_code = f"sz.{code}"
        else:
            bs_code = code

        # Map adjust type
        adjustflag = "3" # qfq default
        if adjust == 'hfq':
            adjustflag = "1"
        elif adjust == 'none':
            adjustflag = "2"
            
        logger.info(f"Querying history for {bs_code} from {start_date} to {end_date}")
        
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
            start_date=start_date, 
            end_date=end_date,
            frequency="d", 
            adjustflag=adjustflag
        )
        
        if rs.error_code != '0':
            return data_source_pb2.DataResponse(
                success=False,
                error_message=f"Baostock query error: {rs.error_msg}"
            )
            
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())
            
        if not data_list:
             return data_source_pb2.DataResponse(
                success=True,
                json_data="[]"
            )
            
        df = pd.DataFrame(data_list, columns=rs.fields)
        return data_source_pb2.DataResponse(
            success=True,
            json_data=df.to_json(orient='records')
        )
        
    def close(self):
        bs.logout()
