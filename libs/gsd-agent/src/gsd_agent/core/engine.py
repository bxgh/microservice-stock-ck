import os
import json
import logging
from typing import Type, TypeVar, Any, Dict, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from gsd_agent.schemas.basic import AgentConfig
from gsd_agent.core.cache import SemanticCache
from gsd_agent.core.prompts import PromptManager

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class SmartDecisionEngine:
    """
    The main entry point for LLM Agent interactions.
    Encapsulates Caching, Routing, and Structured Output.
    """
    
    def __init__(
        self,
        api_keys: Dict[str, str],
        redis_url: str = "redis://localhost:6379/0",
        default_provider: str = "deepseek",
        default_model: str = "deepseek-chat"
    ):
        self.api_keys = api_keys
        self.redis_url = redis_url
        self.default_config = AgentConfig(
            provider=default_provider,
            model_name=default_model,
            api_key=api_keys.get(default_provider)
        )
        
        self.cache = SemanticCache(redis_url)
        self.prompts = PromptManager()
        
        # Clients (Lazy init could be better, but simple dict for now)
        self.clients = {}
        self._init_clients()

    def _init_clients(self):
        # DeepSeek
        if key := self.api_keys.get("deepseek"):
            self.clients["deepseek"] = AsyncOpenAI(
                api_key=key, 
                base_url="https://api.deepseek.com/v1"
            )
        
        # OpenAI
        if key := self.api_keys.get("openai"):
            self.clients["openai"] = AsyncOpenAI(api_key=key)
            
        # SiliconFlow (Qwen free tier)
        if key := self.api_keys.get("siliconflow"):
            self.clients["siliconflow"] = AsyncOpenAI(
                api_key=key,
                base_url="https://api.siliconflow.cn/v1"
            )

    async def run(
        self, 
        prompt_template: str, 
        inputs: Dict[str, Any], 
        response_model: Type[T],
        use_cache: bool = True,
        priority: str = "economy"  # fast, economy, quality
    ) -> T:
        """
        Execute an agent task: Prompt -> LLM -> Structured Pydantic Object
        """
        # 1. Render Prompt
        prompt_text = self.prompts.render(prompt_template, **inputs)
        
        # 2. Determine Router Strategy (Simple fixed logic for now)
        # In a real impl, this would select model based on priority
        current_config = self._route_request(priority)
        
        # 3. Check Cache
        if use_cache:
            cached = self.cache.get(prompt_text, current_config.model_name, response_model)
            if cached:
                logger.debug(f"Cache HIT for {prompt_template}")
                return cached

        # 4. Call LLM (with Retry)
        try:
            result = await self._call_llm_with_retry(
                client_key=current_config.provider,
                model=current_config.model_name,
                prompt=prompt_text,
                temperature=current_config.temperature
            )
            
            
            # 5. Parse JSON (Validation)
            # Clean markdown code fences if present
            cleaned_result = result.strip()
            if cleaned_result.startswith("```"):
                # Remove first line (```json or ```)
                first_newline = cleaned_result.find("\n")
                if first_newline != -1:
                    cleaned_result = cleaned_result[first_newline+1:]
                # Remove last line (```)
                if cleaned_result.endswith("```"):
                    cleaned_result = cleaned_result[:-3].strip()
            
            # Clean control characters (Pydantic validation fails on \u0000-\u001F)
            import re
            cleaned_result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned_result)
            
            parsed_obj = response_model.model_validate_json(cleaned_result)
            
            # 6. Set Cache
            if use_cache:
                self.cache.set(prompt_text, current_config.model_name, parsed_obj)
                
            return parsed_obj
            
        except Exception as e:
            logger.error(f"LLM Call Failed: {e}")
            # Here we could implement fallback logic to a stronger model
            if current_config.fallback_enabled and priority != "quality":
                logger.warning("Attempting fallback to Quality tier...")
                return await self.run(prompt_template, inputs, response_model, use_cache, priority="quality")
            raise

    def _route_request(self, priority: str) -> AgentConfig:
        """Simple Routing Logic"""
        if priority == "fast":
            # Try SiliconFlow/Groq first
            if "siliconflow" in self.clients:
                return AgentConfig(provider="siliconflow", model_name="deepseek-ai/DeepSeek-V3", api_key=self.api_keys.get("siliconflow"))
        
        if priority == "quality":
            # GPT-4 or similar
            if "openai" in self.clients:
                return AgentConfig(provider="openai", model_name="gpt-4o", api_key=self.api_keys.get("openai"))
                
        # Default / Economy -> DeepSeek
        return self.default_config

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_llm_with_retry(self, client_key: str, model: str, prompt: str, temperature: float) -> str:
        client = self.clients.get(client_key)
        if not client:
            raise ValueError(f"Provider {client_key} not configured")
            
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Output pure JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        
        # Some providers (e.g. SiliconFlow Qwen) might not support response_format={"type": "json_object"}
        if client_key != "siliconflow":
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
