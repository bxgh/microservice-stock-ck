import hashlib
import json
import re
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from redis import Redis

T = TypeVar("T", bound=BaseModel)

class SemanticCache:
    """
    Redis-based semantic cache for LLM responses.
    """
    def __init__(self, redis_url: str, ttl_seconds: int = 3600 * 24):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl_seconds

    def _normalize_text(self, text: str) -> str:
        """
        Remove dynamic noise from logs/prompts (timestamps, IPs, random IDs).
        This increases cache hit rate for similar errors.
        """
        # Remove timestamps like 2024-01-01 10:00:00 or [01/Jan/2024...]
        text = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', '', text)
        text = re.sub(r'\[\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}.*?\]', '', text)
        
        # Remove IP addresses
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', text)
        
        # Remove likely random IDs (hex strings > 8 chars)
        text = re.sub(r'\b[0-9a-fA-F]{8,}\b', '<ID>', text)
        
        # Remove Python memory addresses
        text = re.sub(r'0x[0-9a-fA-F]+', '<ADDR>', text)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _generate_key(self, prompt: str, model: str) -> str:
        """MD5 hash of normalized prompt + model config"""
        normalized = self._normalize_text(prompt)
        # Include model schema version if needed, currently just key prompt
        payload = f"{model}:{normalized}"
        return f"llm_cache:v1:{hashlib.md5(payload.encode()).hexdigest()}"

    def get(self, prompt: str, model_name: str, response_model: Type[T]) -> Optional[T]:
        key = self._generate_key(prompt, model_name)
        cached_json = self.redis.get(key)
        if cached_json:
            try:
                # Add a metadata flag to indicate source
                # (Not stored in schema, but useful for debugging if returned raw)
                return response_model.model_validate_json(cached_json)
            except Exception:
                return None
        return None

    def set(self, prompt: str, model_name: str, result: BaseModel):
        key = self._generate_key(prompt, model_name)
        self.redis.setex(key, self.ttl, result.model_dump_json())
