# AkShare 数据源微服务项目文档

## 项目概述
AkShare‑source 微服务负责 **代理** AkShare 公共数据接口，为内部业务提供统一的 HTTP/GRPC 接口。它通过 **Nacos** 注册到服务发现中心，使用 **FastAPI** + **Uvicorn** 提供 RESTful API，后端通过 **aiohttp** 调用外部 AkShare 服务。

## 技术栈
- **语言**: Python 3.12
- **框架**: FastAPI、Uvicorn
- **网络**: aiohttp（异步 HTTP 客户端）
- **服务发现**: Nacos
- **容器**: Docker（基于 `python:3.12‑slim`）
- **代理**: 可选 `proxychains`（通过环境变量 `PROXY_URL`）

## 关键目录结构
```
services/akshare-source/
├─ Dockerfile                # 构建镜像，安装依赖并复制源码
├─ requirements.txt         # 运行时依赖（aiohttp、fastapi、uvicorn 等）
├─ src/
│  ├─ main.py               # 启动入口，加载 gRPC/HTTP 服务
│  └─ service.py            # 实现业务逻辑，封装对 AkShare 的调用
└─ config/
   └─ akshare.yaml          # 可选配置文件（如超时、重试策略）
```

## 主要功能
1. **统一的 REST 接口**：
   - `GET /api/v1/stocks/list` – 获取股票列表
   - `GET /api/v1/market/valuation/{code}/history` – 获取估值历史
   - 其它金融数据接口均通过类似路径暴露。
2. **异步调用**：所有外部请求均使用 `asyncio` + `aiohttp`，确保不阻塞事件循环。
3. **容错与重试**：使用 `tenacity` 实现指数退避重试，配合 `aiohttp.ClientTimeout` 防止长时间卡死。
4. **时区统一**：所有时间均使用 `Asia/Shanghai`（CST），确保业务时序一致。
5. **健康检查**：`GET /api/v1/health` 返回服务状态、版本、启动时间等信息。

## 配置项（环境变量）
| 变量 | 说明 | 示例 |
|------|------|------|
| `AKSHARE_API_URL` | 必填，外部 AkShare 服务入口 | `http://124.221.80.250:8000` |
| `PROXY_URL` | 可选，代理服务器地址 | `http://192.168.151.18:3128` |
| `ENABLE_PROXY` | 是否启用 proxychains，`true`/`false` | `true` |
| `NO_PROXY` | 本地直连的域名列表（逗号分隔） | `localhost,127.0.0.1` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

## 部署说明
1. **构建镜像**（已在 `docker-compose.microservices.yml` 中定义）
   ```bash
   docker build -t akshare-source:latest -f services/akshare-source/Dockerfile .
   ```
2. **启动**（使用 Docker Compose）
   ```bash
   docker compose -f docker-compose.microservices.yml up -d akshare-source
   ```
3. **服务发现**：容器启动后会自动向 Nacos 注册 `akshare-source`，其他微服务可通过 Nacos 获取地址。
4. **日志**：容器日志可通过 `docker logs microservice-stock-akshare-source` 查看，默认输出结构化 JSON。

## 常见问题
- **连接外部 AkShare 超时**：检查 `AKSHARE_API_URL` 是否可达，或确认 `PROXY_URL` 配置是否正确。
- **容器未暴露端口**：服务使用 `host` 网络模式，直接通过宿主机 `127.0.0.1:8083` 访问（实际端口在容器日志中可查）。
- **健康检查失败**：确保 `GET_STOCKDATA_URL` 环境变量指向正确的服务地址，并检查 Nacos 注册是否成功。

---

*本文档旨在为开发、运维和测试人员提供快速上手指南，后续请根据实际需求补充详细的接口文档和性能基准。*
