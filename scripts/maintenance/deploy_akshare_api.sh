#!/bin/bash
# Akshare API 服务部署脚本
# 在腾讯云 Ubuntu 服务器上执行

set -e  # 遇到错误立即退出

echo "========================================="
echo "Akshare API 服务部署脚本"
echo "========================================="

# 检查是否为 root 或有 sudo 权限
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 1. 安装 Python 依赖
echo ""
echo "[1/5] 安装 Python 依赖..."
pip3 install fastapi uvicorn akshare -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 创建工作目录
echo ""
echo "[2/5] 创建工作目录..."
WORK_DIR="/opt/akshare-api"
mkdir -p $WORK_DIR
cd $WORK_DIR

# 检查 akshare_api.py 是否存在
if [ ! -f "akshare_api.py" ]; then
    echo "错误：akshare_api.py 文件不存在！"
    echo "请先将 akshare_api.py 上传到 $WORK_DIR"
    exit 1
fi

# 3. 配置防火墙
echo ""
echo "[3/5] 配置防火墙..."
ufw allow from 218.75.210.182 to any port 8000
ufw reload
echo "✓ 已允许 218.75.210.182 访问 8000 端口"

# 4. 创建 Systemd 服务
echo ""
echo "[4/5] 创建 Systemd 服务..."
cat > /etc/systemd/system/akshare-api.service << 'EOF'
[Unit]
Description=Akshare API Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/akshare-api
ExecStart=/usr/bin/python3 /opt/akshare-api/akshare_api.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/akshare-api.log
StandardError=append:/var/log/akshare-api.error.log

[Install]
WantedBy=multi-user.target
EOF

# 5. 启动服务
echo ""
echo "[5/5] 启动服务..."
systemctl daemon-reload
systemctl enable akshare-api
systemctl restart akshare-api

# 等待服务启动
sleep 3

# 检查服务状态
echo ""
echo "========================================="
echo "服务状态检查:"
echo "========================================="
systemctl status akshare-api --no-pager

# 测试健康检查
echo ""
echo "========================================="
echo "健康检查测试:"
echo "========================================="
curl -s http://localhost:8000/health | python3 -m json.tool || echo "API 可能还在启动中..."

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo "服务地址: http://124.221.80.250:8000"
echo "健康检查: http://124.221.80.250:8000/health"
echo ""
echo "查看日志: sudo journalctl -u akshare-api -f"
echo "重启服务: sudo systemctl restart akshare-api"
echo "停止服务: sudo systemctl stop akshare-api"
