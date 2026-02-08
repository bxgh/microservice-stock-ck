# EPIC-GSF Part 3: Orchestrator Layer + Sub-New Benchmark

**父文档**: [epic_gsf_master.md](./epic_gsf_master.md)  
**状态**: 📝 规划中

---

## 1. 目标

实现编排层 (`SubNewBenchmarkEngine`)，组合 DAO 和 Analyzer，完成次新股对标分析的完整闭环。

---

## 2. User Stories

### Story 3.1: SubNewBenchmarkEngine 核心实现
- **描述**: 编排层引擎，组合所有组件
- **依赖注入**:
  ```python
  class SubNewBenchmarkEngine:
      def __init__(
          self,
          stock_dao: IStockInfoDAO,
          kline_dao: IKLineDAO,
          industry_dao: IIndustryDAO,
          peer_selector: PeerSelector,
          analyzers: List[IAnalyzer]
      ): ...
      
      async def run(self, target_code: str) -> BenchmarkReport: ...
  ```
- **验收标准**: 能为 688802 生成完整报告

### Story 3.2: ReportAggregator 实现
- **描述**: 聚合所有分析器输出，生成结构化报告
- **输出**: `BenchmarkReport`
  ```python
  @dataclass
  class BenchmarkReport:
      target_code: str
      target_info: StockInfo
      peer_count: int
      volatility: VolatilityMetrics
      drawdown: DrawdownMetrics
      multiples: MultiplesMetrics
      beta: BetaMetrics
      liquidity: LiquidityMetrics
      recovery: RecoveryMetrics
      rankings: Dict[str, float]  # 各维度分位数
  ```
- **验收标准**: 报告结构完整

### Story 3.3: Markdown 报告生成器
- **描述**: 将 `BenchmarkReport` 渲染为 Markdown
- **输出路径**: `reports/{stock_code}_{date}.md`
- **验收标准**: Markdown 渲染无语法错误

---

## 3. 文件结构

```
quant-strategy/src/engines/
├── __init__.py
├── subnew_benchmark_engine.py
├── report_aggregator.py
└── markdown_renderer.py
```
