#!/bin/bash
# SSH 免密登录配置脚本
# 用途: 将 Server 41 的公钥复制到 Server 58 和 111

set -e

echo "=== SSH 免密登录配置 ==="
echo ""

# 公钥内容
PUBLIC_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCKkXp2c8RGyDs4F6QkG+fzpAyKhYYOberBZb/7NH5nuv+PlQ+FEzlzjQnNRXQECcYGcrXht7TJfYoWI069JXmmSxTIzc17lkq9i8U/pV+Mt+vl+Um2cyuLpnuLoNDbIYlbB+H88/Qi3W7R007TRgnHm05FdxGXINJigwDDIaHC8YptpMqo1bmiMWGLLEkiFtlisyKUh/oqOr7UxCwQlZr2b3jzXtReMQwGvySECnpbh5vMn7c65i0KWDJ9sazy71cYhWaE7zY80S+7/89ffFqRbC6aIrhd0iu3qCWt6LYYM8DDfsxjgIODym2tGj9rDPZqbou9IpF5RnKCN3ROCjrMDCkxUkP7dYCLVechkbUKhVan7S6913eAtXWAxrDwgMWAN9lmQU04GFv5HI7BFeXZGNpP3W3AZm++BOIdnQpTGjC38gHaaYYAxX7/AjFIhl97s4t9UZJcp6VCGtGobQG/0F914NTorS0sE1ym4HpeqsmufGHIc21uj4awvD5nL68= bxgh@ubuntu24"

echo "请在 Server 58 和 Server 111 上分别执行以下命令:"
echo ""
echo "----------------------------------------"
echo "# 创建 .ssh 目录 (如果不存在)"
echo "mkdir -p ~/.ssh"
echo "chmod 700 ~/.ssh"
echo ""
echo "# 添加公钥到 authorized_keys"
echo "echo '$PUBLIC_KEY' >> ~/.ssh/authorized_keys"
echo "chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "# 验证配置"
echo "tail -1 ~/.ssh/authorized_keys"
echo "----------------------------------------"
echo ""
echo "执行完成后，在 Server 41 上测试连接:"
echo "  ssh root@192.168.151.58 'echo SSH to 58 OK'"
echo "  ssh root@192.168.151.111 'echo SSH to 111 OK'"
