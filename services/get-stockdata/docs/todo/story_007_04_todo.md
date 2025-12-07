# Story 007.04 HistoryService 后续 TODO

## 创建日期: 2025-12-07

---

## 功能增强

### 1. 本地缓存 (P1)
- [ ] 历史数据缓存到 ClickHouse
- [ ] 增量更新策略 (只获取新数据)
- [ ] 缓存过期和刷新机制

### 2. 数据质量 (P1)
- [ ] 数据完整性检查 (缺失交易日)
- [ ] 异常值检测 (涨跌幅超限)
- [ ] 数据源对比校验

### 3. 更多周期 (P2)
- [ ] 年线支持
- [ ] 季度线支持
- [ ] 自定义周期 (如3日线)

---

## 性能优化

### 4. 批量获取 (P2)
- [ ] `get_daily_batch(codes, start, end)` 批量接口
- [ ] 并发请求优化
- [ ] 请求限流控制

### 5. 预加载 (P3)
- [ ] 热门股票历史数据预加载
- [ ] 定时增量更新

---

## 监控告警

### 6. 数据源健康 (P2)
- [ ] baostock 连接状态监控
- [ ] 自动切换 fallback 告警
- [ ] 数据延迟监控

---

## 参考

- [实施报告](../reports/story_007_04_implementation_report.md)
- [EPIC-007 Stories](../plans/epics/epic007_data_service_stories.md)
