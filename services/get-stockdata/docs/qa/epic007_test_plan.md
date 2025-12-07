# EPIC-007 数据服务层测试计划

**版本**: v1.0  
**创建日期**: 2025-12-07  
**状态**: 📝 规划中

---

## 1. 测试范围

### 1.1 服务覆盖

| 服务 | 单元测试 | 集成测试 | 性能测试 |
|------|---------|---------|---------|
| QuotesService | ✅ | ⚠️ | ⚠️ |
| TickService | ✅ | ⚠️ | ⚠️ |
| HistoryService | ✅ | ⚠️ | ⚠️ |
| RankingService | ✅ | ⚠️ | ⚠️ |
| IndexService | ✅ | ⚠️ | ⚠️ |
| SectorService | ✅ | ⚠️ | ⚠️ |
| FinancialService | ✅ | ⚠️ | ⚠️ |
| FundFlowService | ✅ | ⚠️ | ⚠️ |
| TimeAwareStrategy | ✅ | N/A | N/A |

---

## 2. 测试类型

### 2.1 单元测试 (已完成)
- 基础功能验证
- Mock 数据测试
- 边界条件测试

### 2.2 集成测试 (待执行)
- 真实数据源连接
- 端到端数据流
- 服务间协作

### 2.3 性能测试 (待执行)
- 响应时间
- 并发处理
- 缓存命中率

### 2.4 可靠性测试 (待执行)
- 数据源故障恢复
- 超时处理
- 熔断器触发

---

## 3. 集成测试用例

### 3.1 QuotesService

| 用例ID | 描述 | 预期结果 |
|--------|------|----------|
| QS-INT-001 | 获取单只股票行情 | 返回正确价格数据 |
| QS-INT-002 | 批量获取100只行情 | 全部返回，耗时<5s |
| QS-INT-003 | 获取五档盘口 | 返回买卖5档 |
| QS-INT-004 | mootdx故障降级 | 自动切换easyquotation |

### 3.2 TickService

| 用例ID | 描述 | 预期结果 |
|--------|------|----------|
| TS-INT-001 | 获取当日分笔 | 返回分笔列表 |
| TS-INT-002 | 获取历史分笔 | 返回指定日期数据 |
| TS-INT-003 | 分笔摘要统计 | 大单/小单统计正确 |

### 3.3 HistoryService

| 用例ID | 描述 | 预期结果 |
|--------|------|----------|
| HS-INT-001 | 日线数据(无复权) | OHLCV正确 |
| HS-INT-002 | 日线数据(前复权) | 价格已复权 |
| HS-INT-003 | 5分钟K线 | 返回分钟数据 |
| HS-INT-004 | baostock降级mootdx | 自动切换 |

### 3.4 RankingService

| 用例ID | 描述 | 预期结果 |
|--------|------|----------|
| RS-INT-001 | 涨停池 | 返回当日涨停 |
| RS-INT-002 | 龙虎榜 | 返回龙虎榜数据 |
| RS-INT-003 | 连板统计 | 返回连板股票 |
| RS-INT-004 | 人气榜 | 返回100只 |

### 3.5 IndexService

| 用例ID | 描述 | 预期结果 |
|--------|------|----------|
| IS-INT-001 | 沪深300成分股 | 返回300只 |
| IS-INT-002 | 中证500成分股 | 返回500只 |
| IS-INT-003 | ETF持仓 | 返回持仓列表 |

### 3.6 SectorService

| 用例ID | 描述 | 预期结果 |
|--------|------|----------|
| SS-INT-001 | 行业排行 | 返回行业涨幅 |
| SS-INT-002 | 概念排行 | 返回概念涨幅 |
| SS-INT-003 | 板块成分股 | 返回成分股 |

### 3.7 FinancialService

| 用例ID | 描述 | 预期结果 |
|--------|------|----------|
| FS-INT-001 | 财务摘要 | 返回财务指标 |
| FS-INT-002 | PE/PB查询 | 返回估值数据 |

### 3.8 FundFlowService

| 用例ID | 描述 | 预期结果 |
|--------|------|----------|
| FF-INT-001 | 资金流向 | 返回大中小单 |

---

## 4. 性能测试指标

| 服务 | 目标响应时间 | 目标QPS | 目标缓存命中率 |
|------|-------------|---------|---------------|
| QuotesService | <500ms | 10 | >80% |
| TickService | <2s | 5 | >70% |
| HistoryService | <3s | 3 | >90% |
| RankingService | <3s | 2 | >85% |
| SectorService | <5s | 2 | >85% |

---

## 5. 测试环境

```
Docker: docker compose -f docker-compose.dev.yml
Python: 3.12
框架: pytest + pytest-asyncio
```

---

## 6. 执行命令

### 运行所有单元测试
```bash
docker compose -f docker-compose.dev.yml exec get-stockdata \
  pytest tests/data_services/ -v
```

### 运行集成测试
```bash
docker compose -f docker-compose.dev.yml exec get-stockdata \
  pytest tests/data_services/ -v -m integration
```

### 生成覆盖率报告
```bash
docker compose -f docker-compose.dev.yml exec get-stockdata \
  pytest tests/data_services/ --cov=src/data_services --cov-report=html
```
