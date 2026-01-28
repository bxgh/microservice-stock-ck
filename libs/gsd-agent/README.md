# LLM Agent Shared Library

This library encapsulates LLM interactions for the Microservice Stock system.

## Features
- **Smart Decision Engine**: Structured outputs using Pydantic.
- **Model Routing**: Automatic fallback (Groq -> DeepSeek -> OpenAI).
- **Semantic Caching**: Redis-based caching to save costs.

## Usage

```python
from gsd_agent.core import SmartDecisionEngine
from gsd_agent.schemas import OpsDiagnosis

engine = SmartDecisionEngine(
    redis_url="redis://localhost:6379/1",
    api_keys={"deepseek": "sk-...", "openai": "sk-..."}
)

result = await engine.run(
    prompt_template="ops_diagnosis",
    inputs={"logs": "..."},
    response_model=OpsDiagnosis
)
```
