# Story Implementation Plan

**Story ID**: 17.3  
**Story Name**: ClickHouse 存储层结构设计与接口  
**开始日期**: 2026-02-28  
**预期完成**: 2026-02-28  
**负责人**: AI Assistant  
**AI模型**: DeepSeek-V3 (模拟)

---

## 📋 Story概述

### 目标
为采集到的 GitHub 组织仓库的特性指标建立高效快速的时间序列数据库持久化。依照项目架构标准，使用系统中已有的 `ClickHouse` 设立对应的表引擎：一张表用来收集源数据，一张提供后续策略使用的精炼特征信号表。

### 验收标准
- [ ] 执行建表代码 (`github_repo_metrics` 及 `ecosystem_signals`)。遵循 `MergeTree` 引擎配置，配置 `TTL` 防止无限膨胀。
- [ ] 使用异步 `clickhouse-connect` (或异步 `aiochclient`/`httpx`) 批量插入我们刚才 `RepoMetrics` 类的数据。
- [ ] 编写可访问数据库写入成功的 Mock / e2e 测试。
- [ ] 在 `altdata-source` 中导出统一接口（DAO）。

### 依赖关系
- **依赖Story**: Story 17.2 (用于写入的数据来源模型 `RepoMetrics` 已创建)。
- **外部依赖**: 环境现成的本地 ClickHouse（通常通过 Docker port 8123 / 9000 暴露）。

---

## 🎯 需求分析

### 功能需求
1. **自动建表**: 利用 `CREATE TABLE IF NOT EXISTS` 实现应用的自启动创建，减小部署运维压力。
2. **异步写入**: 支持多行指标组合后，通过列存写入 `github_repo_metrics` 库。

### 非功能需求
- **连接池**: 采用连接复用机制提升资源效率。
- **数据留存**: 限定存留一年的 `TTL`。

---

## 🏗️ 技术设计

### 核心组件

#### 组件1: `storage/clickhouse.py`
**职责**: 连接管理、DML/DDL 管理，对接 Pydantic 模型并转换为元组批量插入数据库。

**接口设计**:
```python
class ClickHouseDAO:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        pass

    async def init_tables(self):
        """建库与建表脚本包含 MergeTree 定义及 TTL 限制。"""
        pass
        
    async def insert_metrics(self, metrics_list: List[RepoMetrics]):
        """异步批量插入多维度数据。"""
        pass
```

---

## 📁 文件变更

### 新增文件
- [ ] `services/altdata-source/src/storage/clickhouse.py`
- [ ] `services/altdata-source/tests/test_storage_ch.py`

### 修改文件
- [ ] `services/altdata-source/requirements.txt` (追加 ClickHouse 官方异步库)
- [ ] `services/altdata-source/src/main.py` (在寿命管理器中追加数据库表初始化验证)

---

## 🔄 实现计划

### Phase 1: DAO 开发
**预期时间**: 2 小时
- [ ] 选择并引入 `clickhouse-connect`，实现建表语句。

### Phase 2: 集成与装配
**预期时间**: 1 小时
- [ ] 修改 `main.py` 的 LifeSpan 使得服务具备启动时连线数据库的特性。
- [ ] 完善测试方案并在没有外部 ClickHouse 的独立测试中完成 Mock 检验。

---

## 🧪 测试策略

### 单元测试
- [ ] 针对于 `insert_metrics` 的传参类型转换逻辑做 `BaseModel` -> DB Schema `Dict`的单元验证。
- [ ] 依赖 `MagicMock` 覆盖 DB `execute/query` 组件，避免环境缺少真实的 CH 数据库时直接报错。

---

*模板版本: 1.0*  
