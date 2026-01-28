import asyncio
import os
import sys
from pydantic import BaseModel
from gsd_agent.core.engine import SmartDecisionEngine
from gsd_agent.core.prompts import PromptManager

class SimpleResponse(BaseModel):
    reply: str

async def main():
    print(">>> Initializing SmartDecisionEngine...")
    
    # Force the key from env
    key = os.getenv("SILICONFLOW_API_KEY")
    if not key:
        print("ERROR: SILICONFLOW_API_KEY env var not found!")
        return

    # Initialize engine with just the key we want to test
    engine = SmartDecisionEngine(
        api_keys={"siliconflow": key},
        default_provider="deepseek" # defaults, won't be used with priority='fast'
    )

    # Monkey-patch prompts to add our simple test
    # We want a very simple prompt that ensures JSON output
    engine.prompts = PromptManager({
        "simple_test": """
You are a test assistant.
Please reply with a JSON object containing a single key "reply" with the value "{{ word }}".
Output pure JSON.
"""
    })

    print(f">>> Testing SiliconFlow connection with key: {key[:8]}...")
    
    try:
        result = await engine.run(
            prompt_template="simple_test",
            inputs={"word": "SiliconFlow_Is_Working"},
            response_model=SimpleResponse,
            priority="fast", # This forces SiliconFlow
            use_cache=False
        )
        print(f">>> Success! LLM Reply: {result.reply}")
        
    except Exception as e:
        print(f">>> FAILED with error: {e}")
        # import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    # Ensure src is in path so we can import gsd_agent
    # Assuming this script is at libs/gsd-agent/verify_siliconflow.py
    # and code is at libs/gsd-agent/src
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(current_dir, "src")
    sys.path.append(src_path)
    
    asyncio.run(main())
