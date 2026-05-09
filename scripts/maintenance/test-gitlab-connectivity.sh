#!/bin/bash
# GitLab 连通性测试脚本

echo "=========================================="
echo "GitLab 连通性测试"
echo "=========================================="
echo ""

# 测试本地访问
echo "1️⃣ 本地访问测试 (localhost)"
curl -I http://127.0.0.1:8800 2>&1 | grep "HTTP" || echo "❌ 失败"
echo ""

# 测试通过 ens32 IP 访问
echo "2️⃣ 通过 ens32 访问 (192.168.151.58)"
curl -I http://192.168.151.58:8800 2>&1 | grep "HTTP" || echo "❌ 失败"
echo ""

# 测试 Git 仓库访问
echo "3️⃣ Git 仓库访问测试"
git ls-remote --heads origin 2>&1 | head -1 || echo "❌ 失败"
echo ""

# 测试从 Server 41 访问
echo "4️⃣ 从 Server 41 访问测试"
ssh -o ConnectTimeout=5 bxgh@192.168.151.41 "curl -I http://192.168.151.58:8800 2>&1 | grep HTTP" 2>&1 | grep "HTTP" || echo "❌ 失败或无法连接"
echo ""

# 测试从 Server 111 访问
echo "5️⃣ 从 Server 111 访问测试"
ssh -o ConnectTimeout=5 bxgh@192.168.151.111 "curl -I http://192.168.151.58:8800 2>&1 | grep HTTP" 2>&1 | grep "HTTP" || echo "❌ 失败或无法连接"
echo ""

# 检查 GitLab 容器状态
echo "6️⃣ GitLab 容器状态"
docker ps --filter "name=gitlab" --format "{{.Names}}: {{.Status}}"
echo ""

# 检查端口监听
echo "7️⃣ 端口监听状态"
netstat -tlnp 2>/dev/null | grep 8800 | head -2
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
