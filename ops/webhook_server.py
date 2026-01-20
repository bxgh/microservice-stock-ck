#!/usr/bin/env python3
# ops/webhook_server.py
# 智能 Webhook 接收服务 - 根据变更文件决定部署哪些服务
# 运行方式: nohup python3 ops/webhook_server.py > logs/webhook.log 2>&1 &

import http.server
import socketserver
import subprocess
import os
import json
import logging
import socket
from typing import Set

# 配置
PORT = 9099
SECRET_TOKEN = "123456"
BASE_DIR = "/home/bxgh/microservice-stock/ops"

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# =============================================================================
# 服务与文件路径的映射关系
# =============================================================================
# 定义每个服务受哪些路径影响
SERVICE_PATH_MAPPING = {
    'mootdx-api': [
        'services/mootdx-api/',
        'libs/gsd-shared/',
    ],
    'mootdx-source': [
        'services/mootdx-source/',
    ],
    'gsd-worker': [
        'services/gsd-worker/',
        'libs/gsd-shared/',
    ],
    'shard-poller': [
        'services/task-orchestrator/',
    ],
    'task-orchestrator': [
        'services/task-orchestrator/',
        'libs/gsd-shared/',
    ],
    'quant-strategy': [
        'services/quant-strategy/',
        'libs/gsd-shared/',
    ],
    'get-stockdata': [
        'services/get-stockdata/',
        'libs/gsd-shared/',
    ],
}

# 触发全量部署的路径
FULL_DEPLOY_TRIGGERS = [
    'docker-compose.node-',
    'requirements.txt',
    'Dockerfile',
]

def get_local_ip():
    """获取本机 IP 地址"""
    try:
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
    elif ip in ["192.168.151.58", "192.168.151.55", "192.168.151.56"]:
        return os.path.join(BASE_DIR, "deploy_node_58.sh")
    elif ip in ["192.168.151.111", "192.168.151.36", "192.168.151.37"]:
        return os.path.join(BASE_DIR, "deploy_node_111.sh")
    else:
        logging.warning(f"Unknown IP {ip}, no specific deploy script found.")
        return None

def extract_changed_files(payload: dict) -> Set[str]:
    """从 webhook payload 中提取所有变更的文件路径"""
    changed_files = set()
    
    commits = payload.get('commits', [])
    for commit in commits:
        changed_files.update(commit.get('added', []))
        changed_files.update(commit.get('modified', []))
        changed_files.update(commit.get('removed', []))
    
    return changed_files

def determine_services_to_deploy(changed_files: Set[str], node_ip: str) -> Set[str]:
    """根据变更文件确定需要部署的服务"""
    services = set()
    
    # 检查是否触发全量部署
    for file_path in changed_files:
        for trigger in FULL_DEPLOY_TRIGGERS:
            if trigger in file_path:
                logging.info(f"Full deploy triggered by: {file_path}")
                # 返回该节点的所有服务
                return get_node_services(node_ip)
    
    # 根据路径映射确定服务
    for file_path in changed_files:
        for service, paths in SERVICE_PATH_MAPPING.items():
            for path_prefix in paths:
                if file_path.startswith(path_prefix):
                    services.add(service)
                    logging.info(f"  {file_path} -> {service}")
                    break
    
    # 过滤出该节点支持的服务
    node_services = get_node_services(node_ip)
    filtered = services.intersection(node_services)
    
    return filtered

def get_node_services(node_ip: str) -> Set[str]:
    """获取每个节点支持的服务列表"""
    if node_ip == "192.168.151.41":
        return {'mootdx-api', 'mootdx-source', 'gsd-worker', 'task-orchestrator', 
                'quant-strategy', 'get-stockdata'}
    elif node_ip in ["192.168.151.58", "192.168.151.55", "192.168.151.56"]:
        return {'mootdx-api', 'mootdx-source', 'gsd-worker', 'shard-poller'}
    elif node_ip in ["192.168.151.111", "192.168.151.36", "192.168.151.37"]:
        return {'mootdx-api', 'mootdx-source', 'gsd-worker', 'shard-poller'}
    else:
        return set()

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

        # 2. 读取并解析请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        # 解析 payload
        branch_name = "main"
        services_to_deploy = set()
        
        try:
            payload = json.loads(body.decode('utf-8'))
            
            # 提取分支名
            ref = payload.get('ref', '')
            if ref.startswith('refs/heads/'):
                branch_name = ref.replace('refs/heads/', '')
            
            # 提取变更文件并确定需要部署的服务
            changed_files = extract_changed_files(payload)
            logging.info(f"Changed files ({len(changed_files)}): {list(changed_files)[:10]}...")
            
            node_ip = get_local_ip()
            services_to_deploy = determine_services_to_deploy(changed_files, node_ip)
            
            logging.info(f"Branch: {branch_name}, Services to deploy: {services_to_deploy}")
            
        except json.JSONDecodeError:
            logging.warning("Failed to parse webhook payload, triggering full deploy")
            services_to_deploy = get_node_services(get_local_ip())
        
        # 3. 如果没有需要部署的服务，直接返回
        if not services_to_deploy:
            self.send_response(200)
            self.end_headers()
            msg = f"No services affected for this node (branch: {branch_name})"
            self.wfile.write(msg.encode())
            logging.info(msg)
            return
        
        # 4. 确定并执行部署脚本
        script_path = get_deploy_script()
        
        if not script_path or not os.path.exists(script_path):
            logging.error(f"Deploy script not found: {script_path}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Script not found for this node".encode())
            return

        try:
            os.chmod(script_path, 0o755)
            
            # 将服务列表用逗号连接传递给脚本
            services_arg = ','.join(sorted(services_to_deploy))
            
            # 异步执行，传递分支名和服务列表
            subprocess.Popen(['/bin/bash', script_path, branch_name, services_arg], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            
            self.send_response(200)
            self.end_headers()
            msg = f"Deployment Triggered: {os.path.basename(script_path)} (branch: {branch_name}, services: {services_arg})"
            self.wfile.write(msg.encode())
            logging.info(f"Started: {script_path} with branch={branch_name}, services={services_arg}")
        except Exception as e:
            logging.error(f"Failed to trigger deployment: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Error")

    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

if __name__ == "__main__":
    current_script = get_deploy_script()
    node_ip = get_local_ip()
    node_services = get_node_services(node_ip)
    
    if current_script:
        logging.info(f"Current Node Script: {current_script}")
        logging.info(f"Node Services: {node_services}")
    else:
        logging.warning("No matching deploy script for this node!")

    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        logging.info(f"Serving Smart Webhook at port {PORT}")
        httpd.serve_forever()
