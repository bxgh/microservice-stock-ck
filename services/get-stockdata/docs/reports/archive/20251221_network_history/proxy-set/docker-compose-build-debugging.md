# Docker Compose 构建调试记录

## 概述

本文档记录了调试和解决 `docker compose -f docker-compose-dev.yaml build` 命令失败问题的完整过程。主要问题是 Docker 容器在构建过程中无法通过代理服务器访问外部网络资源。

## 问题背景

### 初始问题
- **命令**: `docker compose -f docker-compose-dev.yaml build`
- **环境**: Ubuntu 24.04 系统，需要通过代理服务器访问网络
- **代理服务器**: `192.168.151.18:3128`
- **错误表现**: 构建过程中无法连接到软件包源，apt-get update 失败

### 环境信息
- **工作目录**: `/home/bxgh/microservice-stock/services/get-stockdata`
- **Docker Compose 文件**: `docker-compose.dev.yml`（注意文件名）
- **Docker 基础镜像**: `python:3.12-slim`
- **用户**: bxgh

## 调试过程

### 第一阶段：问题识别

#### 1. 文件名确认
```bash
# 发现用户提供的文件名与实际文件不符
# 用户：docker-compose-dev.yaml
# 实际：docker-compose.dev.yml

# 使用正确的文件名
docker compose -f docker-compose.dev.yml build
```

#### 2. 初步构建尝试和错误分析
```bash
# 执行构建命令
docker compose -f docker-compose.dev.yml build
```

**错误信息**:
```
Unable to connect to deb.debian.org:http
Connection refused
Could not connect to debian.map.fastlydns.net:80
```

**根因分析**:
- Docker 容器内部无法访问外部网络
- 需要通过代理服务器 `192.168.151.18:3128` 访问
- 容器网络环境与宿主机隔离

### 第二阶段：代理配置

#### 1. Docker daemon 级别代理配置

**解决方案**: 配置 `/etc/docker/daemon.json`

```json
{
  "proxies": {
    "http-proxy": "http://192.168.151.18:3128",
    "https-proxy": "http://192.168.151.18:3128",
    "no-proxy": "localhost,127.0.0.1,::1"
  },
  "dns": ["8.8.8.8", "114.114.114.114"]
}
```

**执行步骤**:
```bash
# 1. 创建或编辑配置文件
sudo nano /etc/docker/daemon.json

# 2. 重启 Docker 服务
sudo systemctl restart docker

# 3. 验证 Docker 服务状态
sudo systemctl status docker
```

#### 2. Dockerfile 代理配置分析

**现有 Dockerfile 代理支持**:
```dockerfile
# 设置代理环境变量（可选，通过build args控制）
ARG ENABLE_PROXY=false
ARG PROXY_URL=http://192.168.151.18:3128

# 根据build args设置代理环境变量
ENV http_proxy=${ENABLE_PROXY:+$PROXY_URL} \
    https_proxy=${ENABLE_PROXY:+$PROXY_URL} \
    HTTP_PROXY=${ENABLE_PROXY:+$PROXY_URL} \
    HTTPS_PROXY=${ENABLE_PROXY:+$PROXY_URL}
```

**apt 代理配置**:
```dockerfile
# 配置apt使用源和代理（可选）
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        export http_proxy=$PROXY_URL && export https_proxy=$PROXY_URL && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    else \
        rm -f /etc/apt/apt.conf.d/00proxy && \
        unset http_proxy && unset https_proxy && \
        sed -i 's|mirrors.aliyun.com|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources || true; \
    fi
```

### 第三阶段：构建验证

#### 1. 使用正确的构建参数
```bash
# 启用代理的构建命令
docker compose -f docker-compose.dev.yml build --build-arg ENABLE_PROXY=true
```

#### 2. 构建过程监控

**成功标志**:
- ✅ apt-get update 成功执行
- ✅ 使用阿里云镜像源 (`mirrors.aliyun.com`)
- ✅ 系统依赖安装完成（curl）
- ✅ pip 升级成功
- ✅ Python 包安装完成

**关键日志输出**:
```
#4 [get-stockdata 4/11] RUN if [ "true" = "true" ]; then...
#4 0.653 Get:1 http://mirrors.aliyun.com/debian trixie InRelease [140 kB]
#4 5.883 Fetched 9987 kB in 5s (1873 kB/s)
#4 DONE 21.7s

#6 [get-stockdata 6/11] RUN pip install --no-cache-dir --upgrade pip...
#6 8.068 Successfully installed pip-25.3

#12 [get-stockdata 8/11] RUN pip install --no-cache-dir -r requirements.txt...
#12 363.5 Successfully installed Mako-1.3.10 MarkupSafe-3.0.3 PyExecJS-1.5.1...
```

### 第四阶段：成功验证

#### 1. 镜像构建完成
```bash
# 检查生成的镜像
docker images | grep get-stockdata

# 输出
get-stockdata    latest    0b982d0d9c5b    About a minute ago    1.2GB
```

#### 2. 构建统计
- **镜像大小**: 1.2GB
- **构建时间**: ~6 分钟
- **安装的包数量**: 150+ 个 Python 包
- **状态**: ✅ 构建成功

## 解决方案总结

### 根本原因
1. **网络隔离**: Docker 容器无法直接使用宿主机的代理配置
2. **DNS 解析**: 容器内 DNS 解析需要优化
3. **代理传递**: Docker daemon 需要明确配置代理设置

### 最终解决方案

#### 1. Docker Daemon 配置（主要）
```json
{
  "proxies": {
    "http-proxy": "http://192.168.151.18:3128",
    "https-proxy": "http://192.168.151.18:3128",
    "no-proxy": "localhost,127.0.0.1,::1"
  },
  "dns": ["8.8.8.8", "114.114.114.114"]
}
```

#### 2. 构建命令
```bash
docker compose -f docker-compose.dev.yml build --build-arg ENABLE_PROXY=true
```

#### 3. Dockerfile 设计优势
- **灵活的代理控制**: 通过 `ENABLE_PROXY` 参数控制
- **镜像源切换**: 自动使用国内镜像源
- **回退机制**: 多个 Python 包源配置

## 技术要点

### 1. Docker 构建代理工作原理
- Docker daemon 负责构建过程的网络请求
- 容器内部的网络环境需要单独配置代理
- 构建参数可以传递环境变量到容器内

### 2. 镜像源优化策略
- **系统包**: 使用阿里云镜像源 (`mirrors.aliyun.com`)
- **Python 包**: 配置多个国内源（清华、阿里云、豆瓣）
- **回退机制**: 源失败时自动尝试下一个

### 3. Docker Compose 配置分析
```yaml
# docker-compose.dev.yml 关键配置
services:
  get-stockdata:
    build:
      context: .
      dockerfile: Dockerfile
    image: get-stockdata:${VERSION:-latest}
    ports:
      - "${SERVICE_PORT:-8086}:8083"
    environment:
      - NACOS_SERVER_URL=${NACOS_SERVER_URL:-http://nacos:8848}
      - ENVIRONMENT=development
    volumes:
      - ./src:/app/src      # 热加载支持
      - ./config:/app/config
    command: >
      uvicorn src.main:app
      --host 0.0.0.0
      --port 8083
      --reload              # 开发模式热加载
```

## 经验教训

### 1. 网络配置
- **Docker daemon 代理**：必须配置，影响构建过程
- **容器内代理**：通过构建参数传递，影响运行时网络
- **DNS 配置**：确保域名解析正常

### 2. 文件命名规范
- **实际文件**：`docker-compose.dev.yml`
- **用户输入**：`docker-compose-dev.yaml`
- **经验**：仔细检查文件名，避免 `.yml` vs `.yaml` 混淆

### 3. 构建参数使用
- **环境变量**：灵活控制构建行为
- **镜像源选择**：根据网络环境自动适配
- **调试信息**：保留详细日志用于问题排查

### 4. 镜像优化建议
- **多阶段构建**：减少最终镜像大小
- **层缓存**：合理利用 Docker 层缓存
- **基础镜像选择**：平衡大小和功能

## 备用方案

### 1. 环境变量方式
```bash
# 设置构建环境变量
export DOCKER_BUILDKIT=1
export HTTP_PROXY=http://192.168.151.18:3128
export HTTPS_PROXY=http://192.168.151.18:3128

# 执行构建
docker compose -f docker-compose.dev.yml build
```

### 2. 构建配置文件
创建 `docker-compose.build.yml` 专门用于构建：
```yaml
services:
  get-stockdata:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        ENABLE_PROXY: true
        PROXY_URL: http://192.168.151.18:3128
      cache_from:
        - get-stockdata:latest
```

### 3. 脚本化构建
```bash
#!/bin/bash
# build.sh

export HTTP_PROXY=http://192.168.151.18:3128
export HTTPS_PROXY=http://192.168.151.18:3128

docker compose \
  -f docker-compose.dev.yml \
  build \
  --build-arg ENABLE_PROXY=true \
  --build-arg PROXY_URL=http://192.168.151.18:3128
```

## 验证清单

### 构建前检查
- [ ] Docker daemon 配置正确
- [ ] 代理服务器可访问
- [ ] 网络连接正常
- [ ] 文件路径正确

### 构建过程监控
- [ ] apt-get update 成功
- [ ] 使用正确的镜像源
- [ ] Python 包下载成功
- [ ] 无网络连接错误

### 构建后验证
- [ ] 镜像生成成功
- [ ] 镜像大小合理
- [ ] 基本功能测试通过
- [ ] 容器可以正常启动

## 相关文件

### 核心文件
- `docker-compose.dev.yml` - 开发环境编排配置
- `Dockerfile` - 镜像构建文件
- `/etc/docker/daemon.json` - Docker 守护进程配置
- `requirements.txt` - Python 依赖列表

### 配置文件
- 代理配置：`192.168.151.18:3128`
- DNS 配置：`8.8.8.8, 114.114.114.114`
- 镜像源：清华大学、阿里云、豆瓣

## 后续优化建议

### 1. 构建性能优化
- 使用 BuildKit 并行构建
- 配置构建缓存
- 优化 Dockerfile 层结构

### 2. 网络稳定性
- 配置多个代理服务器
- 设置网络超时时间
- 实现自动重试机制

### 3. 镜像管理
- 实施镜像版本策略
- 定期清理无用镜像
- 配置镜像仓库

---

**调试完成时间**: 2025-12-04 21:32
**解决问题**: Docker Compose 构建网络连接问题
**关键成功因素**: Docker daemon 代理配置 + 构建参数传递
**文档版本**: v1.0