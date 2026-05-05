import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class JobContext:
    """
    Utility for managing input/output contexts in gsd-worker jobs.
    Enables communication with the Agentic Workflow Orchestrator.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobContext, cls).__new__(cls)
            cls._instance._load_context()
        return cls._instance
    
    def _load_context(self):
        self.raw_input = os.getenv("GSD_INPUT_CONTEXT", "{}")
        try:
            self.input = json.loads(self.raw_input)
        except Exception as e:
            logger.warning(f"Failed to parse GSD_INPUT_CONTEXT: {e}")
            self.input = {}
        
        self.output = {}
        self.cmd_id = os.getenv("GSD_CMD_ID")
        self.run_id = os.getenv("GSD_RUN_ID")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the input context"""
        return self.input.get(key, default)

    def set_output(self, key: str, value: Any):
        """Set a value in the output context to be captured by the orchestrator"""
        self.output[key] = value

    def update_output(self, data: Dict[str, Any]):
        """Update the output context with multiple values"""
        self.output.update(data)

    def flush_output(self):
        """
        Print the output context in a format the orchestrator can capture.
        Should be called at the end of the job.
        """
        if self.output:
            json_str = json.dumps(self.output)
            print(f"\nGSD_OUTPUT_JSON: {json_str}\n")
            logger.info(f"Reported output context: {json_str}")

# Global helper
job_ctx = JobContext()
