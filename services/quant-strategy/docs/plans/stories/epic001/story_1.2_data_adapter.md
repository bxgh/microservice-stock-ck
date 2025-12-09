# Story 1.2: 数据适配层 (Data Adapter)

## 目标
封装 `get-stockdata` 的 API，提供对内的统一 Python 接口。

## 任务分解
1. 实现 `MarketDataProvider` 类，封装行情、K线、财务数据获取接口。
2. 集成 Redis，设计数据缓存机制，减少跨服务调用延迟。
3. 提供数据清洗和格式化工具，标准化为 DataFrame。
4. 编写单元测试，覆盖主要数据获取和缓存逻辑。
5. 补充接口文档，说明各类数据的获取方式和参数。