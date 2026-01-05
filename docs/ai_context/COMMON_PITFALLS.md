# ⚠️ Common Pitfalls & Lessons Learned

> **目的**: 记录开发过程中反复出现的问题模式，帮助 AI 和开发者避免重蹈覆辙。

---

## 🔴 高频问题

### 0. ⚠️ 测试通过但后续使用失败

> 这是一个特别重要的问题模式：**开发时测试成功，但实际运行时失败**。

#### 根因分析

| 类别 | 原因 | 症状 | 解决方案 |
|------|------|------|----------|
| **环境差异** | 测试环境 ≠ 生产环境 | 本地正常，容器内失败 | 始终在 Docker 中测试 |
| **时间依赖** | 测试时在交易时间内，后续不在 | 非交易时间数据为空 | Mock 时间或测试多时段 |
| **数据状态** | 测试时有数据，后续数据状态变化 | 查询返回空或过期数据 | 测试边界条件 |
| **并发竞态** | 单线程测试 OK，并发时失败 | 偶发错误、数据不一致 | 编写并发测试 |
| **外部依赖** | 云端 API 状态变化 | 连接拒绝、超时 | 添加熔断器 |
| **配置漂移** | .env 与容器内不同步 | 连接错误、参数错误 | Volume 挂载配置文件 |
| **资源耗尽** | 连接池/内存泄漏 | 运行一段时间后失败 | 监控 + graceful shutdown |

#### 典型案例

**案例 1: 交易时间问题**
```python
# ❌ 测试时是交易时间，后来不是了
def test_get_realtime_quote():
    data = service.get_quote("600519")
    assert data is not None  # 交易时间内通过，非交易时间失败

# ✅ 正确：Mock 时间或检查交易状态
def test_get_realtime_quote():
    if not is_trading_time():
        pytest.skip("非交易时间跳过")
    data = service.get_quote("600519")
```

**案例 2: 连接池未释放**
```python
# ❌ 测试时连接少，生产跑久了连接耗尽
async def fetch_data():
    conn = await pool.acquire()
    return await conn.execute(query)  # 未释放！

# ✅ 正确：使用 try...finally 或 async with
async def fetch_data():
    async with pool.acquire() as conn:
        return await conn.execute(query)
```

**案例 3: 单例未重置**
```python
# ❌ 第一次测试初始化成功，后续测试复用了脏状态
class Service:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

# ✅ 正确：测试时重置单例
@pytest.fixture(autouse=True)
def reset_singleton():
    Service._instance = None
    yield
    Service._instance = None
```

#### 预防措施

1. **测试覆盖多场景**
   - 交易时间 / 非交易时间
   - 有数据 / 无数据 / 数据异常
   - 单请求 / 并发请求

2. **在 Docker 中测试**
   ```bash
   docker compose -f docker-compose.dev.yml run --rm <service> pytest
   ```

3. **监控长期运行**
   - 内存使用趋势
   - 连接池活跃数
   - 错误率

4. **配置版本控制**
   - `.env` 变更必须更新 `.env.example`
   - 容器使用 volume 挂载配置

---

### 1. 网络连接问题

#### 🌐 网络架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           本地内网环境                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐│
│  │ 开发机器    │     │ 代理服务器   │     │ Docker 容器              ││
│  │ 192.168.x.x │────▶│ 192.168.    ├────▶│ network_mode: host      ││
│  │             │     │ 151.18:3128 │     │ 可访问 127.0.0.1        ││
│  └─────────────┘     └─────────────┘     └─────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           腾讯云环境                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐ │
│  │ MySQL 云端      │  │ Baostock API    │  │ AkShare API          │ │
│  │ 43.145.51.23    │  │ 124.221.80.250  │  │ 124.221.80.250:8003  │ │
│  │ :26300          │  │ :8001           │  │                      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

#### 📍 关键 IP 地址表

| 资源 | 地址 | 用途 | 访问方式 |
|------|------|------|----------|
| **代理服务器** | `192.168.151.18:3128` | 外网访问 | HTTP/HTTPS Proxy |
| **云端 MySQL** | `43.145.51.23:26300` | K线数据源 | SSH 隧道 (本地 36301) |
| **Baostock API** | `124.221.80.250:8001` | 历史 K 线 | 代理 |
| **AkShare API** | `124.221.80.250:8003` | 实时行情 | 代理 |
| **Nacos** | `127.0.0.1:8848` | 服务发现 | host 模式直连 |
| **ClickHouse** | `127.0.0.1:9000` | 时序存储 | host 模式直连 |
| **Redis** | `127.0.0.1:6379` | 缓存 | host 模式直连 |

#### ⚠️ 常见问题矩阵

| 场景 | 症状 | 根因 | 解决方案 |
|------|------|------|----------|
| **容器访问云端 API** | `Connection refused` | 容器内用 127.0.0.1 访问云端 | 使用公网 IP + 代理 |
| **Nacos 注册失败** | `Can't connect to 127.0.0.1:8848` | 非 host 网络模式 | 用 `network_mode: host` 或服务名 |
| **MySQL 云端连接** | 隧道断开 | SSH 隧道不稳定 | 使用 systemd 管理 GOST |
| **API 返回 Mock 数据** | 无法连接远程 | 代理环境变量未设置 | 检查 `HTTP_PROXY` |
| **Docker 镜像拉取失败** | `timeout` | 代理/镜像源问题 | 使用阿里云镜像加速 |
| **pip 安装超时** | `ReadTimeout` | 代理或源慢 | 使用清华源 |

#### 🔧 代理配置要点

```bash
# 必须配置的环境变量
HTTP_PROXY=http://192.168.151.18:3128
HTTPS_PROXY=http://192.168.151.18:3128
NO_PROXY=localhost,127.0.0.1,0.0.0.0,::1,192.168.,10.,172.16.

# Docker 容器内传递 (docker-compose.yml)
environment:
  - HTTP_PROXY=http://192.168.151.18:3128
  - HTTPS_PROXY=http://192.168.151.18:3128
  - NO_PROXY=localhost,127.0.0.1,0.0.0.0,::1,microservice-stock-nacos
```

> ⚠️ **NO_PROXY 必须包含**: `localhost,127.0.0.1` 以及所有内网服务名

#### 🚇 SSH 隧道 (GOST)

云端 MySQL 通过 GOST 隧道访问：

```bash
# 隧道服务配置 (/etc/systemd/system/gost-mysql-tunnel.service)
# 本地 36301 → 代理 → 云端 43.145.51.23:26300

# 检查隧道状态
systemctl status gost-mysql-tunnel

# 测试隧道连通性
mysql -h 127.0.0.1 -P 36301 -u root -p
```

#### 🔍 网络诊断命令

```bash
# 1. 测试代理服务器
curl -v --proxy http://192.168.151.18:3128 https://www.baidu.com

# 2. 测试容器内网络
docker exec <container> curl http://127.0.0.1:8848/nacos/v1/ns/service/list

# 3. 测试云端 API
curl -x http://192.168.151.18:3128 http://124.221.80.250:8003/health

# 4. 测试 MySQL 隧道
nc -zv 127.0.0.1 36301

# 5. 查看容器网络模式
docker inspect <container> | grep NetworkMode
```

**关键教训**:
> 1. 使用 `network_mode: host` 时，容器内可用 127.0.0.1 访问宿主机服务
> 2. 访问外网必须配置代理，访问内网必须加入 NO_PROXY
> 3. 云端 MySQL 必须通过隧道，不能直连

📚 **详细参考**: [internal-network-setup.md](../architecture/internal-network-setup.md)

---

### 2. 端口配置混乱

| 服务 | 易错端口 | 正确端口 | 备注 |
|------|----------|----------|------|
| `get-stockdata` | 8000 | **8083** | 内部端口，外部映射可能不同 |
| `quant-strategy` | 8001 | **8084** | 同上 |
| `gsd-api` | - | **8000** | 这个确实是 8000 |
| `task-orchestrator` | - | **18000** | 区别于其他服务 |

**关键教训**:
> 始终从 `.env` 或 `docker-compose.*.yml` 获取端口，不要凭记忆。

---

### 3. 数据安全踩坑

| 事件 | 后果 | 预防措施 |
|------|------|----------|
| 直接修改 `adjustflag` 默认值 | 历史数据不一致 | 遵循 `data_safety_policy.md` |
| 未授权删除 ClickHouse 数据 | 数据丢失 | 任何 DELETE/ALTER DELETE 必须获批 |
| 同步脚本覆盖原有数据 | 数据被截断 | 使用增量同步而非全量覆盖 |

**关键教训**:
> 📋 见 [data_safety_policy.md](../ai_collaboration/data_safety_policy.md) — **必读**

---

### 4. 异步 & 并发问题

| 问题 | 症状 | 修复方式 |
|------|------|----------|
| **无锁共享状态** | 数据竞争、结果不一致 | 使用 `asyncio.Lock()` |
| **阻塞 I/O** | 事件循环卡死 | 用 `aiohttp` 替代 `requests` |
| **未取消后台任务** | 容器无法正常关闭 | 在 `shutdown` 事件中取消任务 |
| **连接池未关闭** | 连接泄漏 | 实现 `close()` 方法 + try...finally |

**代码示例**:
```python
# ❌ 错误
self._stats = {}  # 无锁

# ✅ 正确
self._lock = asyncio.Lock()
async with self._lock:
    self._stats = {}
```

---

### 5. ClickHouse 特有问题

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| **复制失败** | `Cannot attach replica` | 检查 Keeper 状态 + 9009 端口连通性 |
| **系统日志膨胀** | 磁盘占用 >30GB | 配置 `weekly_clickhouse_log_cleanup` 任务 |
| **表引擎迁移** | 数据丢失风险 | 创建新表 → INSERT SELECT → RENAME |
| **时区问题** | 时间偏移 8 小时 | 显式使用 `Asia/Shanghai` |

---

### 6. Docker 相关问题

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| **容器重启循环** | `Restarting (1)` | 检查日志 `docker logs <container>` |
| **镜像缓存陈旧** | 代码修改不生效 | 使用 `--no-cache` 重建 |
| **挂载权限** | `Permission denied` | 检查宿主机目录权限 |
| **host 模式端口冲突** | `Address already in use` | 停止冲突服务或修改端口 |

---

## 🟡 开发习惯提醒

### 1. 提交前检查清单
- [ ] 运行测试: `docker compose run --rm <service> pytest`
- [ ] 检查 `.env` 变更是否更新了 `.env.example`
- [ ] 确认端口号文档已同步更新

### 2. 调试技巧
```bash
# 查看容器实时日志
docker logs -f <container>

# 进入容器调试
docker exec -it <container> /bin/bash

# 测试端口连通性
docker exec <container> curl -f http://localhost:8083/health

# 查看网络配置
docker network inspect microservice-stock-network
```

### 3. 常用验证命令
```bash
# ClickHouse 连接测试
clickhouse-client --query "SELECT 1"

# Redis 连接测试
redis-cli ping

# 隧道状态检查
systemctl status gost-mysql-tunnel
```

---

### 7. 📈 A 股市场特有问题

> 金融数据系统需要特别处理 A 股市场的特殊规则。

| 场景 | 问题 | 正确处理 |
|------|------|----------|
| **涨跌停** | 涨停买不到、跌停卖不出 | 策略信号需过滤涨跌停股票 |
| **停牌** | 无数据返回或返回停牌前数据 | 检查股票状态，跳过停牌股票 |
| **ST/\*ST股票** | 涨跌幅限制不同 (5% vs 10%) | 单独处理 ST 股票风控规则 |
| **复权因子变化** | 除权除息导致历史数据变化 | 使用原始价格 + 单独的复权因子表 |
| **新股上市** | 无历史数据 | 设置最小数据天数阈值 |
| **集合竞价** | 09:15-09:25 / 14:57-15:00 数据特殊 | 区分连续竞价和集合竞价 |

```python
# ✅ 检查股票状态
def is_tradable(stock_code: str) -> bool:
    quote = get_quote(stock_code)
    if quote is None:
        return False  # 可能停牌
    if quote.pct_change >= 9.9 or quote.pct_change <= -9.9:
        return False  # 涨跌停
    return True
```

---

### 8. 📊 数据质量问题

| 问题 | 症状 | 检测方法 | 处理方式 |
|------|------|----------|----------|
| **数据缺失** | K 线日期不连续 | 比较交易日历与实际数据 | 自动补数据任务 |
| **重复数据** | 同一天多条记录 | `GROUP BY` 聚合检查 | `ReplacingMergeTree` 去重 |
| **异常值** | 涨跌幅 > 20%、成交量 = 0 | 阈值检测 | 标记或过滤 |
| **时间戳错误** | 8 小时偏移 | 与交易时段对比 | 统一使用 Asia/Shanghai |
| **数据源不一致** | mootdx vs baostock 差异 | 交叉验证 | 选定主数据源，定期审计 |

```python
# ✅ 数据质量检查示例
def validate_kline(df: pd.DataFrame) -> list[str]:
    errors = []
    
    # 检查缺失日期
    missing_dates = find_missing_trading_days(df)
    if missing_dates:
        errors.append(f"缺失 {len(missing_dates)} 个交易日")
    
    # 检查异常涨跌幅
    abnormal = df[abs(df['pct_change']) > 11]
    if not abnormal.empty:
        errors.append(f"{len(abnormal)} 条异常涨跌幅记录")
    
    return errors
```

---

### 9. 🤖 AI 开发特有问题

> 这些是 AI Agent 在开发过程中容易犯的错误。

| 问题 | 原因 | 预防措施 |
|------|------|----------|
| **记忆不一致** | 不同会话上下文丢失 | 维护 `ai_context/` 文档 |
| **凭记忆写端口/IP** | 没查配置文件 | 始终从 `.env` 或 `docker-compose.yml` 获取 |
| **跳过测试** | 认为代码逻辑简单 | **强制要求**：所有修改必须有测试 |
| **过度修改** | 修复一个问题引入新问题 | 最小化变更范围 |
| **忽略历史决策** | 不知道为什么这样设计 | 查阅 `DECISION_LOG.md` |
| **重复踩坑** | 不知道之前的问题 | 查阅 `COMMON_PITFALLS.md` (本文档) |

#### AI 开发检查清单

在开始任何开发任务前：
- [ ] 阅读 `QUICK_START.md` 建立上下文
- [ ] 查阅 `COMMON_PITFALLS.md` 了解历史问题
- [ ] 从配置文件获取端口/IP，不要凭记忆

在完成开发任务后：
- [ ] 在 Docker 中运行测试
- [ ] 检查是否引入新问题
- [ ] 更新相关文档（如有必要）
- [ ] 如遇到新坑点，添加到本文档

---

## 📜 历史问题归档

| 日期 | 问题 | 解决方案 | 相关文档 |
|------|------|----------|----------|
| 2026-01-04 | task-orchestrator MySQL 连接失败 | GOST 隧道配置错误 | PROGRESS_REPORT_20260104 |
| 2026-01-04 | mootdx-api IndentationError | 修复语法错误 | PROGRESS_REPORT_20260104 |
| 2026-01-05 | snapshot-recorder 无 graceful shutdown | 实现资源清理 | WALKTHROUGH_SNAPSHOT_RECORDER |

---

> **持续更新**: 遇到新的坑点请添加到本文档，帮助后续开发避坑！
