"""
Prometheus Metrics Middleware

Automatically collects request metrics for all API endpoints.
Records request count, latency, and status for Prometheus scraping.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records Prometheus metrics for each request.
    
    Metrics collected:
    - stockdata_requests_total: Counter of total requests by method, endpoint, status
    - stockdata_request_duration_seconds: Histogram of request latency
    """
    
    # Endpoints to exclude from metrics
    EXCLUDED_PATHS = {
        '/metrics',
        '/health',
        '/favicon.ico',
        '/docs',
        '/openapi.json',
        '/redoc',
    }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip excluded paths
        path = request.url.path
        if path in self.EXCLUDED_PATHS or path.startswith('/static'):
            return await call_next(request)
        
        # Record start time
        start_time = time.perf_counter()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.perf_counter() - start_time
        
        # Record metrics
        try:
            from api.routers.metrics import record_request
            
            # Normalize endpoint path (remove IDs for grouping)
            normalized_path = self._normalize_path(path)
            
            record_request(
                method=request.method,
                endpoint=normalized_path,
                status_code=response.status_code,
                duration=duration
            )
        except ImportError:
            # Metrics module not available, skip
            pass
        except Exception as e:
            # Don't let metrics recording break the request
            logger.warning(f"Error recording metrics: {e}")
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing dynamic segments with placeholders.
        
        Examples:
            /api/v1/stocks/000001 -> /api/v1/stocks/{symbol}
            /api/v1/fenbi/000001/realtime -> /api/v1/fenbi/{symbol}/realtime
        """
        parts = path.split('/')
        normalized = []
        
        for i, part in enumerate(parts):
            if not part:
                continue
            
            # Check if this looks like a stock code (6 digits)
            if part.isdigit() and len(part) == 6:
                normalized.append('{symbol}')
            # Check if this looks like a numeric ID
            elif part.isdigit():
                normalized.append('{id}')
            # Check if this looks like a UUID
            elif len(part) == 36 and part.count('-') == 4:
                normalized.append('{uuid}')
            else:
                normalized.append(part)
        
        return '/' + '/'.join(normalized)
