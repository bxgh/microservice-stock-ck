#!/bin/bash

# Monitoring Exporter Systemd Service Setup Script
# Run with sudo: sudo bash setup_service.sh

SERVICE_NAME="monitoring-exporter"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
WORKING_DIR="/home/bxgh/microservice-stock/services/monitoring-exporter"
PYTHON_BIN="${WORKING_DIR}/.venv/bin/python"
SCRIPT_PATH="${WORKING_DIR}/exporter.py"

echo "🚀 Setting up ${SERVICE_NAME}..."

# Create service file
cat > ${SERVICE_FILE} <<EOF
[Unit]
Description=Monitoring Data Exporter to Cloud MySQL
After=network.target gost-mysql-tunnel.service
Wants=gost-mysql-tunnel.service

[Service]
Type=simple
User=bxgh
WorkingDirectory=${WORKING_DIR}
ExecStart=${PYTHON_BIN} ${SCRIPT_PATH}
Restart=always
RestartSec=60
StandardOutput=append:${WORKING_DIR}/exporter.log
StandardError=append:${WORKING_DIR}/exporter.log

[Install]
WantedBy=multi-user.target
EOF

# Reload and Start
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo "✅ Service ${SERVICE_NAME} installed and started!"
echo "📈 Use 'journalctl -u ${SERVICE_NAME} -f' to see real-time logs."
