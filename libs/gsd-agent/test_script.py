import asyncio
import os
import sys
from gsd_agent.core import SmartDecisionEngine
from gsd_agent.schemas import DiagnosisResult

# 模拟日志数据
SAMPLE_LOG = """
2026-01-25 10:00:01 INFO Starting task sync_tick_shard_0
2026-01-25 10:00:05 ERROR ConnectionResetError: [Errno 104] Connection reset by peer
2026-01-25 10:00:05 WARNING Retrying request to http://192.168.1.10:8888...
2026-01-25 10:00:10 ERROR ReadTimeout: HTTPConnectionPool(host='192.168.1.10', port=8888): Read timed out.
2026-01-25 10:00:10 CRITICAL Job failed after 3 attempts.
"""

async def test_agent():
    print(">>> Initializing SmartDecisionEngine...")
    
    # 注意：这里需要设置环境变量或者直接传入 Key
    # 比如 export OPENAI_API_KEY=sk-... 
    # 为了演示，我们假设环境里有 Key，或者使用 Mock
    
    # engine = SmartDecisionEngine(
    #     api_keys={"deepseek": os.getenv("DEEPSEEK_API_KEY", "mock-key")},
    #     redis_url="redis://localhost:6379/0"
    # )
    
    # MOCK ENGINE for dry-run if no key
    # (In real usage, you'd provide real keys)
    print(">>> [Mock Mode] Assuming valid keys are present in env vars...")
    api_keys = {}
    if os.getenv("DEEPSEEK_API_KEY"): api_keys["deepseek"] = os.getenv("DEEPSEEK_API_KEY")
    if os.getenv("OPENAI_API_KEY"): api_keys["openai"] = os.getenv("OPENAI_API_KEY")
    if os.getenv("SILICONFLOW_API_KEY"): api_keys["siliconflow"] = os.getenv("SILICONFLOW_API_KEY")
    
    if not api_keys:
        print("!!! No API Keys found in ENV. Creating engine but call might fail if not mocked.")
    
    engine = SmartDecisionEngine(
        api_keys=api_keys,
        redis_url="redis://:redis123@localhost:6379/0",
        default_provider="deepseek"  # Or 'siliconflow'
    )
    
    print(f">>> Running Diagnosis on Log (Length: {len(SAMPLE_LOG)} chars)")
    
    try:
        # Mocking the client call strictly for this test script so it runs without real credits
        # Remove this block to test with REAL API
        # ---------------------------------------------------------
        if not api_keys:
            print(">>> Injecting MOCK response for demo purposes...")
            mock_json = """
            {
                "root_cause": "Network instability with the proxy server (Connection Reset/Timeout).",
                "action_type": "RETRY_WITH_PROXY",
                "confidence_score": 0.95,
                "risk_level": 2,
                "reasoning": "The logs show repeated connection resets and timeouts to the proxy IP, typical of a banned or unstable proxy."
            }
            """
            
            from unittest.mock import AsyncMock
            engine._call_llm_with_retry = AsyncMock(return_value=mock_json)
        # ---------------------------------------------------------

        result = await engine.run(
            prompt_template="ops_diagnosis",
            inputs={
                "task_name": "sync_tick_shard_0",
                "timestamp": "2026-01-25 10:00:10",
                "logs": SAMPLE_LOG
            },
            response_model=DiagnosisResult,
            priority="fast",
            use_cache=True
        )
        
        print("\n>>> Analysis Result (Pydantic Object):")
        print(f"  Root Cause: {result.root_cause}")
        print(f"  Action:     {result.action_type}")
        print(f"  Confidence: {result.confidence_score}")
        print(f"  Reasoning:  {result.reasoning}")
        
        # Test Caching
        print("\n>>> Testing Cache (Second Run)...")
        result_2 = await engine.run(
            prompt_template="ops_diagnosis",
            inputs={
                "task_name": "sync_tick_shard_0",
                "timestamp": "2026-01-25 10:00:10",
                "logs": SAMPLE_LOG
            },
            response_model=DiagnosisResult,
            priority="fast",
            use_cache=True
        )
        print(f"  Got Result 2 action: {result_2.action_type}")
        print("  (Success!)")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"!!! Error: {e}")

if __name__ == "__main__":
    # Add src to path so we can import gsd_agent without installing
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    asyncio.run(test_agent())
