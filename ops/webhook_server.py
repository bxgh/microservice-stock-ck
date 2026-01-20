#!/usr/bin/env python3
# ops/webhook_server.py
# 轻量级 Webhook 接收服务
# 运行方式: nohup python3 ops/webhook_server.py > logs/webhook.log 2>&1 &

import http.server
import socketserver
import subprocess
import os
import secrets
import logging
from datetime import datetime

# 配置
PORT = 9099  # 已修改为 9099
SECRET_TOKEN = "123456"  # GitLab Webhook Secret Token
DEPLOY_SCRIPT = "/home/bxgh/microservice-stock/ops/sync_deploy.sh"

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class WebhookHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # 1. 验证 Token (可选)
        token = self.headers.get('X-Gitlab-Token')
        if token != SECRET_TOKEN:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Invalid Token")
            logging.warning(f"Invalid token attempt from {self.client_address}")
            return

        # 2. 读取请求体 (简易处理，不解析具体分支，直接触发同步)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        logging.info(f"Received webhook trigger from {self.client_address}")

        # 3. 异步执行部署脚本
        try:
            # 使用 subprocess.Popen 异步执行，不阻塞 Webhook 响应
            subprocess.Popen(['/bin/bash', DEPLOY_SCRIPT], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Deployment Triggered")
            logging.info("Deployment script started.")
        except Exception as e:
            logging.error(f"Failed to trigger deployment: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Error")

    def log_message(self, format, *args):
        # 覆盖默认日志输出
        logging.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

if __name__ == "__main__":
    # 确保脚本可执行
    if os.path.exists(DEPLOY_SCRIPT):
        os.chmod(DEPLOY_SCRIPT, 0o755)
    
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        logging.info(f"Serving Webhook at port {PORT}")
        logging.info(f"Target Script: {DEPLOY_SCRIPT}")
        httpd.serve_forever()
