#!/bin/bash
# ops/install_webhook_service.sh

# 1. 复制服务文件
echo "Installing webhook-server.service..."
cp ops/webhook-server.service /etc/systemd/system/webhook-server.service

# 2. 重新加载配置
echo "Reloading systemd..."
systemctl daemon-reload

# 3. 启用并启动服务
echo "Enabling and starting service..."
systemctl enable webhook-server.service
systemctl restart webhook-server.service

# 4. 检查状态
echo "Checking status..."
systemctl status webhook-server.service --no-pager
