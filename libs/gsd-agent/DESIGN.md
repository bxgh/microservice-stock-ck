# LLM Agent Shared Library (`gsd-agent`) 设计与实施方案

> **版本**: 1.0 (Draft)  
> **日期**: 2026-01-25  
> **目标**: 将 LLM 调用、路由、缓存及结构化输出封装为通用的 Python 共享库，供 Orchestrator 和 Strategy 等服务调用。

---

## 1. 设计理念

采用 **"Library-as-a-Service" (LaaS)** 模式，而非独立的微服务。

*   **轻量级 Integration**: 直接嵌入业务代码，零网络开销。
*   **统一 Governance**: 集中管理 Prompt、模型路由策略和计费缓存。
*   **强类型 Contract**: 强制 Pydantic 输入输出，拒绝“字符串编程”。

---

## 2. 目录结构

该库将位于项目根目录的 `libs/` 下，与 `gsd-shared` 并列。

```text
libs/
└── gsd-agent/
    ├── src/
    │   └── gsd_agent/
    │       ├── __init__.py
    │       ├── core/
    │       │   ├── engine.py       # 核心引擎 (LLM调用入口)
    │       │   ├── router.py       # 模型路由与降级逻辑 (Route & Fallback)
    │       │   ├── cache.py        # 语义缓存实现 (Semantic Caching)
    │       │   └── providers.py    # 适配器 (OpenAI, DeepSeek, Groq)
    │       ├── schemas/            # Pydantic 模型定义
    │       │   └── basic.py
    │       ├── prompts/            # 全局 Prompt 模板仓库
    │       │   └── ops_diagnosis.py
    │       └── utils/
    ├── pyproject.toml              # 依赖管理 (poetry/pip)
    └── README.md
```

---

## 3. 核心功能模块设计

### 3.1 智能引擎 (`SmartDecisionEngine`)
对外暴露的统一 Facade。

```python
# Usage Example
from gsd_agent.core import SmartDecisionEngine
from gsd_agent.schemas import OpsDiagnosis

engine = SmartDecisionEngine(
    redis_url="redis://localhost:6379/1",
    api_keys={"deepseek": "sk-...", "openai": "sk-..."}
)

# 像调用普通函数一样调用 LLM
decision = await engine.run(
    prompt_template="ops_diagnosis",
    inputs={"logs": log_content},
    response_model=OpsDiagnosis  # 泛型支持，自动解析为该类型
)
```

### 3.2 路由策略 (`ModelRouter`)
实现成本优先与高可用并重的路由逻辑。

*   **Level 1 (Free/Fast)**: Groq (Llama-3), SiliconCloud (Qwen-7B)
*   **Level 2 (Economy)**: DeepSeek-V3, Qwen-Turbo
*   **Level 3 (Premium)**: GPT-4o, Claude-3.5
*   **Fallback Logic**:
    1.  优先尝试配置策略中定义的 `primary` 模型。
    2.  如果遇到 `ConnectionError`, `Timeout`, `JSONDecodeError`，自动降级到下一级模型。
    3.  使用 `tenacity` 库实现带 jitter 的指数退避重试。

### 3.3 语义缓存 (`SemanticCache`)
避免重复扣费，提升响应速度。

*   **Key 生成**: `md5(normalize(system_prompt + user_prompt))`
    *   `normalize`: 移除日志中的时间戳、随机 ID、IP 地址等高频变动噪声。
*   **存储**: Redis `SETEX`，默认 TTL 24小时。
*   **Hit/Miss**:
    *   Hit: 直接返回 JSON 反序列化后的 Object，标记 `_metadata.cached=True`。
    *   Miss: 调用 Router，成功后写入 Redis。

---

### 4. 数据模型 (Schemas)

标准化所有交互数据。

#### 4.1 基础配置
```python
class AgentConfig(BaseModel):
    provider: Literal["openai", "deepseek", "groq", "siliconflow"] = "deepseek"
    model_name: str
    temperature: float = 0.1
    timeout: int = 30
    fallback_enabled: bool = True
```

#### 4.2 运维自愈 (Ops) 场景
```python
class DiagnosisResult(BaseModel):
    """运维诊断结果"""
    root_cause: str = Field(description="根本原因分析")
    action_type: Literal["RETRY", "ROTATE_PROXY", "SKIP", "ALERT"]
    confidence_score: float = Field(ge=0, le=1)
    retry_delay_seconds: int = 0
```

---

## 5. 依赖清单

`libs/gsd-agent/pyproject.toml`

```toml
[tool.poetry.dependencies]
python = "^3.12"
openai = "^1.10.0"       # 标准 SDK，兼容 DeepSeek/Moonshot
pydantic = "^2.6.0"      # 数据验证
tenacity = "^8.2.0"      # 重试逻辑
redis = "^5.0.0"         # 缓存后端
jinja2 = "^3.1.0"        # Prompt 模板渲染
```

---

## 6. 实施计划

1.  **初始化 (Day 1)**:
    *   在 `libs/` 下创建骨架。
    *   实现 `SemanticCache` 和 `ModelRouter` 基础版。
2.  **对接 (Day 2)**:
    *   在 `task-orchestrator` 中引入库。
    *   创建一个简单的“日志诊断”测试用例验证连通性。
3.  **扩展 (Day 3+)**:
    *   添加更多的 Prompt 模板和 Schema。
    *   在 `quant-strategy` 中复用。

---
**备注**: 此方案遵循“保持简单”原则，不引入 LangChain 等重型框架，完全通过轻量级 Python 代码控制 LLM 交互细节。
