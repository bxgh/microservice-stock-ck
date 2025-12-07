"""
API中间件
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# 认证
security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    验证API Token
    """
    from config.settings import settings

    # 如果没有配置API Key，则跳过验证
    if not settings.api_key:
        return credentials

    if not credentials or credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials


async def verify_api_key(request: Request, call_next):
    """
    API Key验证中间件
    """
    from config.settings import settings

    # 如果没有配置API Key，则跳过验证
    if not settings.api_key:
        return await call_next(request)

    # 检查Authorization头
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证Bearer Token
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer" or token != settings.api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    response = await call_next(request)
    return response


async def add_cors_headers(request: Request, call_next):
    """
    CORS中间件
    """
    response = await call_next(request)

    # 添加CORS头
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"

    return response


async def log_requests(request: Request, call_next):
    """
    请求日志中间件
    """
    import time

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)

    return response
