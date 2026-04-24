## Epic 7: API 层

### Epic 目标

构建 **REST API**,供前端和第三方系统调用。

### Stories

---

#### Story 7.1: FastAPI 应用骨架

```python
# backend/src/cci_monitor/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .v1 import cci, layers, backtest, system
from ..core.logger import setup_logging, logger
from ..core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("API starting")
    yield
    await engine.dispose()
    logger.info("API shutdown")

app = FastAPI(
    title="CCI Monitor API",
    description="A股相变监测 REST API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://cci.yourdomain.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 路由
app.include_router(cci.router, prefix="/api/v1/cci", tags=["cci"])
app.include_router(layers.router, prefix="/api/v1/layers", tags=["layers"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])

# 统一错误处理
from ..core.exceptions import CCIError

@app.exception_handler(CCIError)
async def cci_error_handler(request, exc: CCIError):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.code,
            "message": str(exc),
            "context": exc.context,
        },
    )
```

**预计工时:** 3 小时

---

#### Story 7.2: 核心 API 端点

**端点清单:**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/cci/latest` | 最新 CCI |
| GET | `/api/v1/cci/history` | CCI 历史(支持 layer 过滤) |
| GET | `/api/v1/layers/latest` | 所有层级最新快照 |
| GET | `/api/v1/layers/{id}/history` | 指定层级历史 |
| GET | `/api/v1/layers/{id}/components` | 层级监测对象 |
| GET | `/api/v1/backtest/latest` | 最新回测结果 |
| POST | `/api/v1/backtest/run` | 触发回测 |
| GET | `/api/v1/alerts/recent` | 最近预警 |
| GET | `/api/v1/dislocations/recent` | 最近层级错位 |
| GET | `/api/v1/system/health` | 健康检查 |
| POST | `/api/v1/system/refresh` | 手动触发计算 |

**预计工时:** 6 小时

---

#### Story 7.3: API 认证与限流 (3h)

即使个人使用,也要最基本的 API Key 保护。使用 FastAPI Security + slowapi。

---

