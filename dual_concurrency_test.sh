#!/bin/bash

echo "=== 启动双通道并发测试 ==="

# 通道1: 直接连接 (Server 41 直连)
echo "🚀 启动通道1 (Direct)..."
docker run -d --rm --network host --name worker_direct \
  --env-file .env \
  -e MOOTDX_API_URL=http://127.0.0.1:8003 \
  -e CLICKHOUSE_HOST=127.0.0.1 \
  -v $(pwd)/services/gsd-worker/src:/app/src \
  gsd-worker:latest \
  python -m jobs.sync_tick --concurrency 1 --date 20260109 --scope config --shard-total 100 --shard-index 0 \
  > /tmp/worker_direct.log 2>&1

# 通道2: 代理连接 (通过 192.168.151.18)
# 注意：我们需要在容器内设置 HTTP_PROXY 环境变量，并且确保 MOOTDX_API_URL 走代理
# 但是 mootdx 是 TCP 协议，HTTP_PROXY 对它是无效的，除非 mootdx 库支持 SOCKS 代理。
# 这里有一个假设：如果 192.168.151.18 能够转发 TCP 流量，或者 mootdx 支持代理配置。
# 检查 mootdx 源码或配置发现它主要使用 socket 直连。
# 如果代理是 HTTP 代理，仅能代理 HTTP 请求。 TDX 是 TCP。
# 这意味着必须使用 *系统级* 代理如 proxychains 或者 transparent proxy。
# 或者，如果 mootdx API 实际上是在容器 *内部* 调用的？不，mootdx-api 是独立服务。
# 真正受限的是 mootdx-api (Server) 到 TDX (External) 的连接。

# 修正思路：
# 我们需要启动 *两个* mootdx-api 服务。
# API-1: 直连外网。 (Port 8003)
# API-2: 通过代理连接外网。 (Port 8004)
# 如果我们能让 API-2 走代理，我们就赢了。

# 如何让 Docker 容器内的 TCP 连接走 HTTP 代理？
# 通常很难，除非使用 SOCKS5。 3128 通常是 Squid (HTTP)。
# 所以，唯一的希望是 Server 111 的 IP 不同。

# 重新验证 Server 111 IP，这次用最简单的命令，不依赖外网 DNS
ssh bxgh@192.168.151.111 "curl -s http://checkip.amazonaws.com"
curl -s http://checkip.amazonaws.com

