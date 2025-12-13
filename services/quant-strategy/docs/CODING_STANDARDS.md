# Quant Strategy 项目编码规范

## 核心原则

### 1. 真实数据优先 ⭐ **强制规则**

**规则**: 禁止使用Mock数据进行测试

**原因**:
- 避免技术债务积累
- Mock数据可能与实际API不一致
- 测试结果不可靠
- 后续需要重写测试

**替代方案**:
- ✅ 使用真实的StockDataProvider获取实际数据
- ✅ 编写集成测试而非单元测试(必要时)
- ✅ 使用测试环境的真实API

**示例**:
```python
# ❌ 错误 - 使用Mock
@patch('data_provider.get_quotes')
def test_strategy(mock_get):
    mock_get.return_value = fake_data
    
# ✅ 正确 - 使用真实数据
async def test_strategy_with_real_data():
    provider = StockDataProvider()
    await provider.initialize()
    df = await provider.get_realtime_quotes(['600519'])
    # 使用真实数据测试
```

---

### 2. Docker容器测试 ⭐ **强制规则**

**规则**: 所有测试必须在Docker容器内运行

**原因**:
- 确保环境一致性
- 避免"我这里能跑"问题
- 依赖管理统一
- 生产环境一致

**执行方式**:
```bash
# ✅ 正确 - Docker内运行测试
docker exec quant-strategy-dev pytest tests/

# ❌ 错误 - 本地运行测试
pytest tests/  # 禁止
```

**CI/CD要求**:
- 所有CI/CD pipeline必须在Docker环境执行
- 本地开发也必须使用Docker测试
- 测试报告从容器内生成

---

### 3. 异步优先

**规则**: 所有I/O操作必须使用async/await

**原因**: Python 3.12+, asyncio是标准，性能更好

---

### 3. 类型提示强制

**规则**: 所有函数必须有类型提示

```python
# ✅ 正确
async def get_signals(codes: List[str]) -> List[Signal]:
    pass
```

---

### 4. 错误处理

**规则**: 
- 使用`try...finally`确保资源释放
- 日志记录足够的上下文信息
- 优雅降级，不要让服务crash

---

### 5. 并发安全

**规则**:
- 共享状态必须使用`asyncio.Lock()`
- 避免全局可变状态

---

### 6. 数据验证

**规则**: 使用`DataValidator`验证所有外部数据

```python
from adapters.data_utils import validate_quotes

df = await provider.get_realtime_quotes(codes)
df = validate_quotes(df)  # 必须验证
```

---

### 7. 数据库规范 (腾讯云 MySQL) ⭐ **强制规则**

**目标数据库**: 腾讯云 MySQL
- **Host**: `sh-cdb-h7flpxu4.sql.tencentcdb.com`
- **Port**: `26300`
- **Database**: `alwaysup`

**规则**:
1. **所有业务数据必须持久化到腾讯云 MySQL**，而非本地 SQLite
2. 开发环境可使用 SQLite 进行快速迭代，但 **生产环境强制使用 MySQL**
3. 使用 `database_type="mysql"` 配置项切换

**配置方式**:
```python
# .env 文件配置
QS_DATABASE_TYPE=mysql
QS_DB_HOST=sh-cdb-h7flpxu4.sql.tencentcdb.com
QS_DB_PORT=26300
QS_DB_USER=root
QS_DB_PASSWORD=xxx  # 使用环境变量，禁止硬编码
QS_DB_NAME=alwaysup
```

**异步连接**:
```python
# 使用 aiomysql 驱动
DATABASE_URL = "mysql+aiomysql://user:pass@host:port/db"
```

**必须遵守**:
- ✅ 使用 SQLAlchemy 异步 ORM
- ✅ 连接池大小 ≤ 10 (避免超过云数据库限制)
- ✅ 所有查询带超时 (10s)
- ❌ 禁止在代码中硬编码数据库密码

---

### 8. 任务调度规范 ⭐ **强制规则**

**规则**: 定时任务由 `task-scheduler` 微服务统一管理

**禁止**:
- ❌ 在服务内部使用 APScheduler 或 BackgroundScheduler 进行定时任务
- ❌ 使用 `asyncio.create_task()` 实现周期性后台任务

**正确方式**:
```python
# 暴露 API 端点供 task-scheduler 调用
@router.post("/api/v1/jobs/refresh-pool")
async def trigger_refresh():
    return await pool_service.refresh()
```

**task-scheduler 配置**:
```yaml
jobs:
  - name: refresh_universe_pool
    cron: "0 22 * * 0"  # 每周日 22:00
    target:
      service: quant-strategy
      endpoint: /api/v1/pools/universe/refresh
      method: POST
```

## 安全规范 ⭐ 强制要求

### 密钥管理

**规则**: 禁止硬编码密钥

```python
# ❌ 错误 - 硬编码
api_key = "sk-abc123..."

# ✅ 正确 - 环境变量
import os
api_key = os.getenv('API_KEY')
if not api_key:
    raise ValueError("API_KEY not configured")
```

**最佳实践**:
- 使用环境变量或密钥管理服务
- `.env`文件必须在`.gitignore`
- 生产密钥与开发密钥分离
- 定期轮换密钥

### 敏感数据保护

**规则**: 日志和错误消息中不得包含敏感信息

```python
# ❌ 错误 - 泄露密码
logger.error(f"Login failed for {username} with password {password}")

# ✅ 正确 - 脱敏
logger.error(f"Login failed for {username}")
```

**敏感数据清单**:
- 密码、API密钥、Token
- 身份证号、手机号
- 交易账户信息
- 个人财务数据

### SQL注入防护

**规则**: 使用参数化查询

```python
# ❌ 错误 - SQL注入风险
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 正确 - 参数化
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

---

## 日志规范

### 日志级别

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **DEBUG** | 调试信息 | 变量值、函数调用 |
| **INFO** | 正常流程 | 策略启动、信号生成 |
| **WARNING** | 可恢复错误 | API超时重试、缓存失效 |
| **ERROR** | 业务错误 | 数据验证失败、策略异常 |
| **CRITICAL** | 系统故障 | 数据库连接失败 |

### 日志格式

**标准格式**:
```python
import logging

logger = logging.getLogger(__name__)

# ✅ 正确格式
logger.info(
    "Signal generated",
    extra={
        'strategy': 'MA_Strategy',
        'stock_code': '600519',
        'signal_type': 'LONG',
        'score': 85.5
    }
)
```

**必须包含**:
- 时间戳 (ISO 8601格式)
- 日志级别
- 模块名
- 消息
- 上下文信息 (extra字段)

### 敏感信息脱敏

```python
def mask_sensitive(data: str) -> str:
    """脱敏处理"""
    if len(data) <= 4:
        return "***"
    return data[:2] + "***" + data[-2:]

# ✅ 使用
logger.info(f"User {mask_sensitive(phone)} logged in")
```

---

## 错误处理规范

### 错误分类

**1. 业务错误** (可预期)
- 数据验证失败
- 权限不足
- 策略参数无效

**处理**: 返回错误码，记录WARNING

**2. 系统错误** (不可预期)
- 数据库连接失败
- 第三方API超时
- 内存不足

**处理**: 记录ERROR，尝试重试或降级

**3. 致命错误** (不可恢复)
- 配置文件缺失
- 依赖服务全部不可用

**处理**: 记录CRITICAL，服务启动失败

### 错误码规范

```python
class ErrorCode:
    # 业务错误 (1xxx)
    INVALID_STOCK_CODE = 1001
    INVALID_PARAMETER = 1002
    
    # 系统错误 (2xxx)
    DATABASE_ERROR = 2001
    API_TIMEOUT = 2002
    
    # 第三方错误 (3xxx)
    DATA_SOURCE_UNAVAILABLE = 3001
```

### 错误处理模板

```python
async def generate_signals(codes: List[str]) -> List[Signal]:
    try:
        # 业务逻辑
        df = await provider.get_quotes(codes)
        return calculate_signals(df)
        
    except ValueError as e:
        # 业务错误
        logger.warning(f"Invalid input: {e}")
        return []
        
    except ConnectionError as e:
        # 系统错误 - 重试
        logger.error(f"Connection failed: {e}, retrying...")
        await asyncio.sleep(1)
        return await generate_signals(codes)  # 重试
        
    except Exception as e:
        # 未知错误
        logger.exception(f"Unexpected error: {e}")
        raise
        
    finally:
        # 确保资源释放
        await provider.close()
```

### 用户友好的错误消息

```python
# ❌ 错误 - 技术细节暴露
raise ValueError("pandas.DataFrame.loc[...] KeyError: 'price'")

# ✅ 正确 - 用户可理解
raise ValueError("行情数据缺少价格字段，请检查数据源")
```

---

## 测试规范

### 测试分层策略 ⭐ 重要

**分层定义**:

#### 1. 单元测试 (Unit Tests)
**适用场景**: 纯逻辑、无外部依赖的函数
- ✅ 允许使用Mock (仅限此层)
- ✅ 测试单一函数/方法
- ✅ 快速执行 (< 100ms/测试)

**示例**:
```python
def test_signal_validation():
    # ✅ 允许Mock - 纯逻辑测试
    signal = Signal(code='600519', type='LONG', score=85)
    assert signal.is_valid()
```

#### 2. 集成测试 (Integration Tests) ⭐ 主要测试
**适用场景**: 跨组件、有外部依赖的完整流程
- ✅ **必须使用真实数据**
- ✅ 测试完整数据流 (数据获取 → 策略计算 → 信号生成)
- ✅ 在Docker环境运行
- ✅ 允许较长执行时间 (< 5s/测试)

**示例**:
```python
async def test_strategy_end_to_end():
    # ✅ 真实数据 - 完整流程
    provider = StockDataProvider()
    await provider.initialize()
    df = await provider.get_realtime_quotes(['600519'])
    
    strategy = MAStrategy()
    signals = await strategy.generate_signals(df)
    assert len(signals) >= 0
```

#### 3. 性能测试 (Performance Tests)
**适用场景**: 验证性能指标
- ✅ 测试响应时间、吞吐量
- ✅ 使用真实数据规模
- ✅ 并发场景测试

**测试比例建议**:
- 单元测试: 20%
- 集成测试: 70% (主要)
- 性能测试: 10%

### 覆盖率要求

- **核心模块** (strategies/, core/): ≥ 90%
- **工具模块** (adapters/, utils/): ≥ 80%
- **配置文件**: ≥ 60%

---

## 性能指标 ⭐ 强制要求

### API响应时间

| 操作 | P50 | P95 | P99 | 超时 |
|-----|-----|-----|-----|------|
| 获取实时行情 | < 50ms | < 100ms | < 200ms | 30s |
| 生成交易信号 | < 100ms | < 200ms | < 500ms | 60s |
| 数据库查询 | < 20ms | < 50ms | < 100ms | 10s |
| Redis缓存 | < 5ms | < 10ms | < 20ms | 5s |

### 吞吐量要求

- **并发策略数**: ≥ 10个策略同时运行
- **股票池规模**: 支持1000+股票实时监控
- **信号生成频率**: 每分钟 ≥ 100个信号

### 资源限制

- **内存使用**: 单策略 < 500MB
- **CPU使用**: 单核 < 80% (持续)
- **数据库连接**: 连接池 ≤ 20个

### 测试验证

```python
# 性能测试示例
async def test_signal_generation_performance():
    import time
    
    start = time.time()
    signals = await strategy.generate_signals(large_dataset)
    elapsed = time.time() - start
    
    assert elapsed < 0.2  # P95: 200ms
    assert len(signals) > 0
```

### 性能监控

- 使用`@profile`装饰器记录关键路径
- 周性能报告自动生成
- 超标自动告警

---

## 文档规范

### Docstring格式

```python
async def generate_signals(self, df: pd.DataFrame) -> List[Signal]:
    """
    生成交易信号
    
    Args:
        df: 市场数据DataFrame
        
    Returns:
        Signal对象列表
        
    Raises:
        ValueError: 数据验证失败
    """
```

---

## Git提交规范

遵循Conventional Commits:
- `feat:` 新功能
- `fix:` Bug修复
- `docs:` 文档更新
- `test:` 测试相关
- `refactor:` 重构

---

**更新**: 2025-12-12  
**审核**: 必须遵守
