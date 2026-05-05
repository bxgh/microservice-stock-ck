# Epic 1: 数据层精化与验证

## 现状
已实现 `MySQLDataClient` 基础框架，包含 `httpx` 调用和基本的 `field_mapping`。

## 目标
确保数据获取链路在高并发下的稳定性，完善本地 Parquet 缓存策略，确保 K 线数据标准化。

## Stories

### Story 1.1: 完善 MySQLDataClient 的鲁棒性
**As a** 数据引擎
**I want** 在调用 `get-stockdata` API 时具备完善的错误处理和超时机制
**So that** 外部服务故障不导致本项目崩溃

- **实现**：集成 `resilience.py` 中的重试装饰器到 `api_client.py`。
- **验收**：通过 Mock API 故障测试重试逻辑。

### Story 1.2: 实施本地高效 Parquet 缓存
**As a** 计算服务
**I want** 将获取的 K 线数据持久化为本地 Parquet 文件
**So that** 在进行历史回测或重复计算时无需频繁调用网络接口

- **实现**：在 `CachedDataSource` 中集成 `cache.py` 逻辑。
- **规则**：历史日期（D-2 之前）永久缓存，近期数据 TTL 为 1 小时。

### Story 1.3: 数据标准化与时区一致性
- **实现**：确保所有输出 DataFrame 的日期格式为 `YYYY-MM-DD`，时区强制为 `Asia/Shanghai`。
- **验收**：单元测试验证输出字段包含 `date, open, high, low, close, volume, change_pct`。
