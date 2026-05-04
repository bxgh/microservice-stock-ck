import logging
import asyncio
from datetime import datetime
from typing import Optional
import httpx
import pytz
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings

logger = logging.getLogger(__name__)
TZ = pytz.timezone(settings.TIMEZONE)

class Notifier:
    """
    Alert Notifier
    Supports local logging and external Webhooks (Feishu/WeCom/DingTalk).
    """
    
    _instance = None
    _email_lock = asyncio.Lock()  # 用于保护 socket monkey-patch
    
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
            
        # 2. Send Email (Primary)
        if settings.EMAIL_USER and settings.EMAIL_PASSWORD:
            asyncio.create_task(self._send_email(title, message, level))
            
        # 3. Send to external system (Webhook - Backup)
        if settings.NOTIFIER_WEBHOOK_URL:
            asyncio.create_task(self._send_webhook(title, message, level))
    
    async def _send_email(self, title: str, message: str, level: str) -> None:
        """
        Send notification via SMTP Email.
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.header import Header

        icon = "🚨" if level == "error" else "⚠️" if level == "warning" else "ℹ️"
        subject = f"{icon} {title}"
        current_time = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
        body = f"告警级别: {level.upper()}\n发生时间: {current_time}\n\n内容:\n{message}"
        
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = settings.EMAIL_TO

        try:
            # 使用锁确保 socket monkey-patch 的原子性
            async with self._email_lock:
                # 封装为线程运行，避免阻塞事件循环
                await asyncio.to_thread(self._do_send_email, msg)
            logger.debug("✓ Email notification sent successfully")
        except Exception as e:
            logger.error(f"❌ Failed to send Email: {e}")

    def _do_send_email(self, msg):
        import smtplib
        import socks
        import socket

        # 核心逻辑：在内网环境下，通过 gost-foreign (127.0.0.1:8118) 建立隧道
        # 理由：国内 Squid 代理 (3128) 禁用了 465 端口的 CONNECT，而国外通道 (8118) 允许。
        proxy_host = "127.0.0.1"
        proxy_port = 8118
        
        # 记录原始 socket 构造函数
        _orig_socket = socket.socket
        
        try:
            # 动态设置全局代理 (仅限当前线程/作用域)
            socks.set_default_proxy(socks.HTTP, proxy_host, proxy_port)
            socket.socket = socks.socksocket
            
            # 正常执行 SMTP 逻辑
            if settings.EMAIL_PORT == 465:
                with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                    server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                    if settings.EMAIL_PORT == 587:
                        server.starttls()
                    server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
                    server.send_message(msg)
                    
            logger.debug("✓ Email sent via HTTP Proxy (8118)")
            
        except Exception as e:
            logger.error(f"❌ SMTP Proxy error: {e}")
            raise
        finally:
            # 还原 socket 构造函数，避免干扰其他模块
            socket.socket = _orig_socket

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _send_webhook(self, title: str, message: str, level: str) -> None:
        """
        Send notification via Webhook.
        Default format is Markdown (compatible with WeCom/Feishu).
        """
        if not settings.NOTIFIER_WEBHOOK_URL:
            return

        icon = "🚨" if level == "error" else "⚠️" if level == "warning" else "ℹ️"
        
        # WeCom / Feishu compatible Markdown
        current_time = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### {icon} {title}\n**Level**: {level.upper()}\n**Time**: {current_time}\n\n{message}"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(settings.NOTIFIER_WEBHOOK_URL, json=payload)
                response.raise_for_status()
                logger.debug(f"✓ Webhook notification sent: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to send Webhook: {e}")
            raise  # Re-raise for tenacity retry

notifier = Notifier()
