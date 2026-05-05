from jinja2 import Environment, DictLoader

# Embedded default prompts
DEFAULT_PROMPTS = {
    "ops_diagnosis": """
You are an expert SRE (Site Reliability Engineer) for a financial data system.
Your task is to analyze the following error logs and recommend a recovery action.

CONTEXT:
Task Name: {{ task_name }}
Timestamp: {{ timestamp }}

LOGS:
{{ logs }}

INSTRUCTIONS:
1. Analyze the root cause. Distinguish between:
   - Network issues (timeouts, resets) -> Suggest RETRY or ROTATE_PROXY
   - Data source issues (404, empty data) -> Suggest SKIP or ALERT
   - System/Code issues (bugs, OOM) -> Suggest ALERT_ADMIN
2. Determine risk level (1-10).
3. If it's a known transient issue, suggest RETRY.
4. If proxy seems banned, suggest ROTATE_PROXY.

Return pure JSON matching the following schema:
{
  "root_cause": "string",
  "action_type": "RETRY_IMMEDIATE" | "RETRY_WITH_PROXY" | "SKIP" | "ALERT_ADMIN",
  "confidence_score": 0.0-1.0,
  "risk_level": 1-10,
  "reasoning": "string"
}
"""
}

class PromptManager:
    def __init__(self, custom_prompts: dict = None):
        sources = DEFAULT_PROMPTS.copy()
        if custom_prompts:
            sources.update(custom_prompts)
        
        self.env = Environment(loader=DictLoader(sources))

    def render(self, template_name: str, **kwargs) -> str:
        template = self.env.get_template(template_name)
        return template.render(**kwargs)
