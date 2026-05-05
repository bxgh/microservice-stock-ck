# Story Implementation Plan

**Story ID**: 17.2  
**Story Name**: GitHub API 数据采集器  
**开始日期**: 2026-02-28  
**预期完成**: 2026-02-28  
**负责人**: AI Assistant  
**AI模型**: DeepSeek-V3 (模拟)

---

## 📋 Story概述

### 目标
实现 `altdata-source` 服务的核心功能：针对指定的 GitHub 目标仓库进行数据采集。涵盖 API 的并发调用、Token 的轮换及 Rate Limit 控制，并最终输出 `pr_merged_count`、`pr_merged_acceleration` 等 6 项特征加工逻辑。

### 验收标准
- [ ] 实现 `GitHubCollector` 类 (异步 + httpx)。支持 HTTP Keep-Alive 和高效并发。
- [ ] 具备 Token 多令牌自动轮换：检查响应头 `X-RateLimit-Remaining`。
- [ ] 能够成功提取指定的 6 项特征：`pr_merged_count`, `pr_merged_acceleration`, `issue_close_median_hours`, `star_delta_7d`, `commit_count_7d`, `contributor_count_30d`。
- [ ] 支持通过读取外部 YAML (或 Pydantic模型) 来配置待抓取的 `org/repo`。
- [ ] 针对单仓储抓取失败具备良好的容错抛出（不影响其他仓库抓取）。
- [ ] 提供单元测试，通过 Mock 拦截 HTTP 数据来校验采集计算逻辑。

### 依赖关系
- **依赖Story**: Story 17.1 (基础环境与配置)
- **外部依赖**: GitHub REST API v3。不依赖任何自身数据存储。

---

## 🎯 需求分析

### 功能需求
1. **统一的 HttpClient 配置**: 处理 `Authorization: Bearer <token>` 及 `Accept: application/vnd.github.v3+json`。
2. **多线程/协程并发管控**: 限制对 GitHub 接口并发访问数以防止直接触发防滥用封控（推荐并发度暂定 5-10 之间）。
3. **分页支持**: 诸如 `commits` 与 `issues` 往往需要按时间边界分页抓取，需要通用分页游标遍历器。
4. **指标计算加工**: 
   - `pr_merged_acceleration` = 本周(7天)减去 上周(14~7天)
   - `issue_close_median_hours` = 对指定时间窗口内的 `closed` Issues 计算响应时长中位数。

### 非功能需求
- **重试机制**: Retry，指数退避（避免网络偶发抖动导致的单次采集失败）。
- **可观测性**: 严谨打点 `logger.info/warning`，便于排查 Token 耗尽和特定库的变更问题。

---

## 🏗️ 技术设计

### 核心组件

#### 组件1: `core/github_client.py` 
**职责**: 底层 HTTP 会话包装，处理 Token 耗尽后的轮流切换，处理 Github Web API 特有的各种异常与重试。

**接口设计**:
```python
class GitHubClient:
    def __init__(self, tokens: List[str]):
        # ...

    async def get(self, url_path: str, params: dict = None) -> dict/list:
        """支持自动分页、限流监控与重试机制的 HTTP GET"""
        pass
```

#### 组件2: `collectors/github.py`
**职责**: 调用 `GitHubClient` 对每个 `org/repo` 组装业务请求，最终返回所需特征组。

**接口设计**:
```python
from pydantic import BaseModel

class RepoMetrics(BaseModel):
    org: str
    repo: str
    label: str
    pr_merged_count: int
    pr_merged_acceleration: int
    issue_close_median_hours: float
    star_delta_7d: int
    commit_count_7d: int
    contributor_count_30d: int

class GitHubCollector:
    async def collect_repo(self, org: str, repo: str, label: str) -> RepoMetrics:
        """聚合拉取指定仓库的所有指标并合并返回"""
        pass
```

---

## 📁 文件变更

### 新增文件
- [ ] `services/altdata-source/src/core/github_client.py`
- [ ] `services/altdata-source/src/collectors/github.py`
- [ ] `services/altdata-source/src/models/metrics.py` (存放 Pydantic 表现形式)
- [ ] `services/altdata-source/src/config/repositories.yaml` (默认目标配置)
- [ ] `services/altdata-source/src/core/dependencies.py` (读取配置与初始化 Collector 的依赖)
- [ ] `services/altdata-source/tests/test_github_client.py`
- [ ] `services/altdata-source/tests/test_github_collector.py`

### 修改文件
- [ ] `services/altdata-source/requirements.txt` (追加 PyYAML、pytest、pytest-asyncio 等组件)

---

## 🔄 实现计划

### Phase 1: 客户端与模型
**预期时间**: 4 小时
- [ ] 定义 `RepoMetrics` 模型。
- [ ] 实现并测试带重试与 Token 轮换的底层 `GitHubClient`。

### Phase 2: 采集器业务逻辑
**预期时间**: 4 小时
- [ ] 编写获取并计算 6 项特征逻辑的方法（特别是 PR 的 14 天对比、Issues 取中位数的过程）。
- [ ] 综合拼装出 `GitHubCollector`。

### Phase 3: 配置解析与单元测试
**预期时间**: 2 小时
- [ ] 编写能够加载 `repositories.yaml` 的工具。
- [ ] 使用 `respx` 或 `pytest-httpx` 处理模拟 HTTP 网络调用。

---

## 🧪 测试策略

### 单元测试覆盖
- [ ] **Token轮换测试**: 模拟前两次返回 `X-RateLimit-Remaining: 0`，观测客户端是否智能切换下一个可以访问的 Token。
- [ ] **重试机制测试**: 模拟 502/503 网络报错，测试重试库策略。
- [ ] **计算逻辑覆盖**: 输入已知的 Issue closed/created 时间数据，断言中位数方法 `issue_close_median_hours` 输出正确结果。

---

## 🚨 风险与缓解

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|----------|
| Github API 频繁分页导致超时 | 高 | 中 | 采用并行并发执行不同 API（如分别拉 Issue 和 PR），并且限制每项最大查询回溯深度。 |
| 无法通过 `pytest` 自动 mock | 低 | 中 | 手动硬编码引入 `respx` / `pytest-httpx` 拦截 HTTPx 调用，避免脏请求发出。 |

---

*模板版本: 1.0*  
