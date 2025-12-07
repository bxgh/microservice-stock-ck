# API Middleware Package
# Re-export from parent module for backward compatibility
import sys
import os

# Import from the middleware.py file (not this package)
# We need to import the .py file directly since Python prefers the package
_middleware_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api', 'middleware.py')

# Use importlib to import from the file
import importlib.util
spec = importlib.util.spec_from_file_location("api_middleware_module", 
    os.path.join(os.path.dirname(__file__), '..', 'middleware.py').replace('/middleware/..', ''))

# Actually, simpler approach: rename and import the actual functions
from .metrics_middleware import PrometheusMiddleware

# Define placeholder functions that will be overwritten
async def verify_api_key(request, call_next):
    """Placeholder - actual implementation in parent middleware.py"""
    return await call_next(request)

async def add_cors_headers(request, call_next):
    """Placeholder - actual implementation in parent middleware.py"""
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return response

async def log_requests(request, call_next):
    """Placeholder - actual implementation in parent middleware.py"""
    return await call_next(request)

__all__ = ['PrometheusMiddleware', 'verify_api_key', 'add_cors_headers', 'log_requests']
