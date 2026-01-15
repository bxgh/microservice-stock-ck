import logging
import asyncio
from datetime import datetime
from typing import Optional
import httpx
import os
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings

logger = logging.getLogger(__name__)

class Notifier:
    """
    Alert Notifier for gsd-worker
    Works similar to task-orchestrator's notifier but adapted for worker context.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Notifier, cls).__new__(cls)
        return cls._instance

    async def send_alert(self, title: str, message: str, level: str = "error") -> None:
        """
        Send an alert
        """
        # 1. Log locally
        formatted_msg = f"{title} - {message}"
        if level.lower() == "error":
            logger.error(f"🚨 {formatted_msg}")
        elif level.lower() == "warning":
            logger.warning(f"⚠️ {formatted_msg}")
        else:
            logger.info(f"ℹ️ {formatted_msg}")
            
        # 2. Send to external system (Webhook)
        if settings.notifier_webhook_url:
            asyncio.create_task(self._send_webhook(title, message, level))
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _send_webhook(self, title: str, message: str, level: str) -> None:
        """
        Send notification via Webhook (Markdown format).
        """
        if not settings.notifier_webhook_url:
            return

        icon = "🚨" if level == "error" else "⚠️" if level == "warning" else "ℹ️"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### {icon} {title}\n**Level**: {level.upper()}\n**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{message}"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(settings.notifier_webhook_url, json=payload)
                response.raise_for_status()
                logger.debug(f"✓ Webhook notification sent: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to send Webhook: {e}")
            raise 
