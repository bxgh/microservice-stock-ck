## Epic 0: 项目基础设施

### Epic 目标

建立项目的**基础设施层**:依赖管理、配置、日志、异常、数据库连接、Docker 环境。
没有这一步,上面的代码跑不起来。

### Stories

---

#### Story 0.1: 项目初始化与依赖管理

**As a** 开发者
**I want** 一个标准化的 Python 项目骨架
**So that** 所有开发者开箱即用,依赖版本一致

**技术实现:**

- 使用 `uv` (推荐) 或 `poetry` 管理依赖
- `pyproject.toml` 完整声明项目元数据
- 区分生产依赖 / 开发依赖 / 可选依赖

**验收标准:**
- [ ] `uv sync` 或 `poetry install` 一键安装所有依赖
- [ ] `pyproject.toml` 中有完整的项目描述、作者、许可证
- [ ] 有 `[tool.ruff]` 和 `[tool.mypy]` 的配置
- [ ] 有 `.python-version` 或类似的 Python 版本固定
- [ ] `.gitignore` 覆盖 `.venv/` `data/` `logs/` `.env` 等

**预计工时:** 2 小时

---

#### Story 0.2: 配置管理系统

**As a** 开发者
**I want** 类型安全的配置系统
**So that** 所有参数都有明确的类型和默认值,环境切换不出错

**技术实现:**

```python
# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from pathlib import Path
from typing import Literal

class DataSettings(BaseSettings):
    primary_source: Literal["akshare", "tushare"] = "akshare"
    tushare_token: SecretStr | None = None
    cache_dir: Path = Path("data/cache")
    cache_ttl_hours: int = 24
    request_timeout: int = 30
    max_retries: int = 3

class SignalSettings(BaseSettings):
    variance_short_window: int = 20
    variance_long_window: int = 60
    variance_threshold: float = 1.5
    autocorr_window: int = 60
    autocorr_threshold: float = 0.15
    skew_window: int = 60
    skew_threshold: float = 1.0
    correlation_window: int = 20
    correlation_stock_count: int = 300

class CCISettings(BaseSettings):
    alpha_weight: float = 0.4
    beta_weight: float = 0.3
    gamma_weight: float = 0.2
    delta_weight: float = 0.1
    alert_threshold_l1: float = 0.7
    alert_threshold_l2: float = 1.0
    alert_threshold_l3: float = 1.3

class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://cci:cci@localhost:5432/cci_monitor"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10

class NotificationSettings(BaseSettings):
    server_chan_key: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_to: str | None = None
    enable_daily_report: bool = True

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
    
    env: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    data: DataSettings = DataSettings()
    signal: SignalSettings = SignalSettings()
    cci: CCISettings = CCISettings()
    database: DatabaseSettings = DatabaseSettings()
    notification: NotificationSettings = NotificationSettings()

# 单例
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**`.env.example`:**

```bash
# ==== 环境 ====
ENV=dev
LOG_LEVEL=INFO

# ==== 数据源 ====
DATA__PRIMARY_SOURCE=akshare
DATA__CACHE_DIR=data/cache

# ==== 数据库 ====
DATABASE__URL=postgresql+asyncpg://cci:cci@localhost:5432/cci_monitor

# ==== 推送(可选)====
NOTIFICATION__SERVER_CHAN_KEY=
NOTIFICATION__SMTP_HOST=
NOTIFICATION__SMTP_USER=
NOTIFICATION__SMTP_TO=
```

**验收标准:**
- [ ] 支持嵌套配置(`DATA__PRIMARY_SOURCE` 语法)
- [ ] 敏感配置使用 `SecretStr`
- [ ] `get_settings()` 是 `lru_cache` 单例
- [ ] 有对应的单元测试(mock 环境变量)
- [ ] `.env.example` 覆盖所有可配置项

**预计工时:** 3 小时

---

#### Story 0.3: 日志系统

**技术实现:**

```python
# backend/src/cci_monitor/core/logger.py
from loguru import logger
from config.settings import get_settings
import sys

def setup_logging():
    settings = get_settings()
    logger.remove()  # 清除默认
    
    # 控制台输出
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level:8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "{message}",
    )
    
    # 文件输出(按日期滚动)
    logger.add(
        "logs/cci_{time:YYYY-MM-DD}.log",
        level=settings.log_level,
        rotation="00:00",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:8} | "
               "{name}:{function}:{line} | {message}",
    )
    
    # 生产环境错误单独文件
    if settings.env == "prod":
        logger.add(
            "logs/cci_error_{time:YYYY-MM-DD}.log",
            level="ERROR",
            rotation="00:00",
            retention="90 days",
        )

# 便捷导出
__all__ = ["logger", "setup_logging"]
```

**验收标准:**
- [ ] 启动时一次性配置
- [ ] 日志文件按日期滚动
- [ ] 生产环境错误日志单独文件
- [ ] 支持结构化字段(`logger.info("X", x=1, y=2)`)

**预计工时:** 2 小时

---

#### Story 0.4: 异常层级

**技术实现:**

```python
# backend/src/cci_monitor/core/exceptions.py

class CCIError(Exception):
    """项目所有异常的基类."""
    code: str = "CCI_ERROR"
    
    def __init__(self, message: str, **context):
        super().__init__(message)
        self.context = context

# === 数据源异常 ===
class DataSourceError(CCIError):
    code = "DATA_SOURCE_ERROR"

class DataSourceEmptyError(DataSourceError):
    code = "DATA_SOURCE_EMPTY"

class DataSourceTimeoutError(DataSourceError):
    code = "DATA_SOURCE_TIMEOUT"

class DataSourceUnavailableError(DataSourceError):
    code = "DATA_SOURCE_UNAVAILABLE"

class DataSourceRateLimitError(DataSourceError):
    code = "DATA_SOURCE_RATE_LIMIT"

# === 信号异常 ===
class SignalError(CCIError):
    code = "SIGNAL_ERROR"

class InsufficientDataError(SignalError):
    code = "INSUFFICIENT_DATA"

# === 配置异常 ===
class ConfigurationError(CCIError):
    code = "CONFIG_ERROR"

# === 数据库异常 ===
class DatabaseError(CCIError):
    code = "DATABASE_ERROR"
```

**验收标准:**
- [ ] 所有异常有唯一 code 字段(用于 API 响应)
- [ ] 支持 context 字段传递额外信息

**预计工时:** 1 小时

---

#### Story 0.5: 数据库连接与 ORM 基础

**技术实现:**

```python
# backend/src/cci_monitor/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database.url,
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

@asynccontextmanager
async def get_db_session() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**ORM 模型示例(为 CCI 结果):**

```python
# backend/src/cci_monitor/db/models.py
from sqlalchemy import String, Float, Integer, Date, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date, datetime
from backend.src.cci_monitor.core.database import Base

class CCIRecord(Base):
    __tablename__ = "cci_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    layer_id: Mapped[int] = mapped_column(Integer, index=True)
    
    cci: Mapped[float]
    alpha: Mapped[float]
    beta: Mapped[float]
    gamma: Mapped[float]
    delta: Mapped[float]
    
    alert_level: Mapped[int]
    alert_label: Mapped[str] = mapped_column(String(20))
    
    # 诊断字段
    market_rho: Mapped[float | None]
    resonant_rho: Mapped[float | None]
    deep_rho: Mapped[float | None]
    delta_rho: Mapped[float | None]
    up_down_ratio: Mapped[float | None]
    
    # 扩展存储
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    
    computed_at: Mapped[datetime]
    
    __table_args__ = (
        UniqueConstraint("date", "layer_id", name="uq_date_layer"),
        Index("ix_date_layer", "date", "layer_id"),
    )

class AlertRecord(Base):
    __tablename__ = "alert_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    triggered_at: Mapped[datetime] = mapped_column(index=True)
    alert_level: Mapped[int]
    layer_id: Mapped[int]
    cci_value: Mapped[float]
    message: Mapped[str]
    context_json: Mapped[dict | None] = mapped_column(JSON)
    notified: Mapped[bool] = mapped_column(default=False)

class DislocationRecord(Base):
    __tablename__ = "dislocation_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(index=True)
    dislocation_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[int]
    involved_layers: Mapped[list[int]] = mapped_column(JSON)
    description: Mapped[str]
```

**验收标准:**
- [ ] 使用 async SQLAlchemy 2.0 语法
- [ ] 所有模型有必要的索引
- [ ] 有 Alembic 初始化迁移
- [ ] 提供 `init_db.py` 脚本用于初始化

**预计工时:** 4 小时

---

#### Story 0.6: Docker 化

**技术实现:**

```yaml
# docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: cci
      POSTGRES_PASSWORD: cci
      POSTGRES_DB: cci_monitor
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cci"]
      interval: 10s
  
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
      - ./data:/app/data
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    command: uvicorn cci_monitor.api.main:app --host 0.0.0.0 --port 8000 --reload
  
  scheduler:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    command: python scripts/start_scheduler.py
  
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      VITE_API_URL: http://localhost:8000
  
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/caddy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
      - frontend

volumes:
  pg_data:
  caddy_data:
  caddy_config:
```

**验收标准:**
- [ ] `docker-compose up -d` 一键启动所有服务
- [ ] 服务之间通过健康检查正确依赖
- [ ] 数据持久化(重启后数据不丢)
- [ ] Caddy 自动 HTTPS(生产部署)

**预计工时:** 4 小时

**依赖:** 0.1-0.5

---

