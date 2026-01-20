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
import socket

# 配置
PORT = 9099
SECRET_TOKEN = "123456"
# 基础路径
BASE_DIR = "/home/bxgh/microservice-stock/ops"

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_local_ip():
    """获取本机 IP 地址"""
    try:
        # 创建一个 UDP 套接字，连接到外部地址来探测本机 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_deploy_script():
    """根据 IP 获取对应的部署脚本"""
    ip = get_local_ip()
    logging.info(f"Detected Local IP: {ip}")
    
    if ip == "192.168.151.41":
        return os.path.join(BASE_DIR, "deploy_node_41.sh")
    elif ip == "192.168.151.58":
        return os.path.join(BASE_DIR, "deploy_node_58.sh")
    elif ip == "192.168.151.111":
        return os.path.join(BASE_DIR, "deploy_node_111.sh")
    else:
        # 本地开发或未知环境，默认不执行危险操作，或者回退到 41 脚本(如果是开发机)
        # 这里为了安全，返回 None 或默认脚本
        logging.warning(f"Unknown IP {ip}, no specific deploy script found.")
        return None

class WebhookHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # 1. 验证 Token
        token = self.headers.get('X-Gitlab-Token')
        if token != SECRET_TOKEN:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Invalid Token")
            logging.warning(f"Invalid token attempt from {self.client_address}")
            return

        # 2. 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        _ = self.rfile.read(content_length)
        logging.info(f"Received webhook trigger from {self.client_address}")

        # 3. 确定并执行部署脚本
        script_path = get_deploy_script()
        
        if not script_path or not os.path.exists(script_path):
            logging.error(f"Deploy script not found or IP not matched: {script_path}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Script not found for this node".encode())
            return

        try:
            # 确保脚本有执行权限
            os.chmod(script_path, 0o755)
            
            # 异步执行
            subprocess.Popen(['/bin/bash', script_path], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Deployment Triggered: {os.path.basename(script_path)}".encode())
            logging.info(f"Started deployment script: {script_path}")
        except Exception as e:
            logging.error(f"Failed to trigger deployment: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Error")

    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

if __name__ == "__main__":
    current_script = get_deploy_script()
    if current_script:
        logging.info(f"Current Node Script: {current_script}")
    else:
        logging.warning("No matching deploy script for this node!")

    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        logging.info(f"Serving Smart Webhook at port {PORT}")
        httpd.serve_forever()
