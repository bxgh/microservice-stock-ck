# 内网开发环境配置指南

## 🌐 网络环境概述

本项目的开发部署环境为**内部网络**，需要通过代理服务器访问外部互联网资源。

### 网络配置
- **代理服务器**: `192.168.151.18:3128`
- **协议**: HTTP/HTTPS
- **用途**: 访问外部API、下载依赖包、拉取Docker镜像

## 🔧 代理配置

### 1. 系统环境变量

开发人员需要配置以下环境变量：

```bash
# HTTP/HTTPS代理配置
export HTTP_PROXY=http://192.168.151.18:3128
export HTTPS_PROXY=http://192.168.151.18:3128

# 绕过代理的内网地址
export NO_PROXY=localhost,127.0.0.1,0.0.0.0,192.168.,10.,172.16.

# Docker代理配置
export DOCKER_HTTP_PROXY=http://192.168.151.18:3128
export DOCKER_HTTPS_PROXY=http://192.168.151.18:3128
export DOCKER_NO_PROXY=localhost,127.0.0.1,0.0.0.0
```

### 2. Git配置

```bash
# Git代理配置
git config --global http.proxy http://192.168.151.18:3128
git config --global https.proxy http://192.168.151.18:3128

# 取消代理配置（如需要）
# git config --global --unset http.proxy
# git config --global --unset https.proxy
```

### 3. Python包管理器

#### pip配置文件 `~/.pip/pip.conf`
```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
proxy = http://192.168.151.18:3128
timeout = 120
```

#### conda配置
```bash
# conda代理配置
conda config --set proxy_servers.http http://192.168.151.18:3128
conda config --set proxy_servers.https http://192.168.151.18:3128

# 使用清华镜像源
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
```

## 🐳 Docker配置

### 1. Docker daemon配置

创建或编辑 `/etc/docker/daemon.json`：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ],
  "proxies": {
    "http-proxy": "http://192.168.151.18:3128",
    "https-proxy": "http://192.168.151.18:3128",
    "no-proxy": "localhost,127.0.0.1,0.0.0.0,192.168.,10.,172.16."
  },
  "insecure-registries": [],
  "debug": false,
  "experimental": false
}
```

重启Docker服务：
```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 2. Docker Compose配置

在 `docker-compose.yml` 中使用国内镜像：

```yaml
version: '3.8'

services:
  # MySQL使用国内镜像
  mysql:
    image: registry.cn-hangzhou.aliyuncs.com/library/mysql:8.0
    # 或使用中科大镜像
    # image: docker.mirrors.ustc.edu.cn/library/mysql:8.0

  # Redis使用国内镜像
  redis:
    image: registry.cn-hangzhou.aliyuncs.com/library/redis:7.2-alpine

  # ClickHouse使用官方镜像（需要代理）
  clickhouse:
    image: yandex/clickhouse-server:latest
    build:
      context: ./docker/clickhouse
      args:
        HTTP_PROXY: http://192.168.151.18:3128
        HTTPS_PROXY: http://192.168.151.18:3128
```

### 3. 镜像加速方案

#### 方案1：使用阿里云镜像加速
```bash
# 配置阿里云镜像加速器
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": ["https://registry.cn-hangzhou.aliyuncs.com"]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 方案2：使用中科大镜像
```bash
# 修改Dockerfile使用国内基础镜像
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.12-slim
```

## 📦 Node.js/NPM配置

### npm配置文件 `~/.npmrc`
```
registry=https://registry.npmmirror.com
proxy=http://192.168.151.18:3128
https-proxy=http://192.168.151.18:3128

# 临时取消代理
# npm config delete proxy
# npm config delete https-proxy
```

### yarn配置
```bash
yarn config set registry https://registry.npmmirror.com
yarn config set proxy http://192.168.151.18:3128
yarn config set httpsProxy http://192.168.151.18:3128
```

## 🐍 Python项目配置

### requirements.txt中使用国内源
```bash
# 在pip install时指定国内源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 或永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### conda环境配置
```bash
# 创建环境时使用国内镜像
conda create -n microservice-stock python=3.12 -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/

# 更新conda配置
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
conda config --set channel_priority strict
```

## 🌐 外部API访问

### 股票数据API
项目需要访问的外部API需要通过代理：

```python
import requests

# 股票数据服务示例代码
proxies = {
    'http': 'http://192.168.151.18:3128',
    'https': 'http://192.168.151.18:3128'
}

# Alpha Vantage API
response = requests.get(
    'https://www.alphavantage.co/query',
    params={'function': 'TIME_SERIES_DAILY', 'symbol': 'AAPL'},
    proxies=proxies,
    timeout=30
)

# Yahoo Finance API
response = requests.get(
    'https://query1.finance.yahoo.com/v8/finance/chart/AAPL',
    proxies=proxies,
    timeout=30
)
```

## 🔍 网络故障排查

### 常见问题及解决方案

#### 1. Docker镜像拉取失败
```bash
# 检查代理配置
curl -v --proxy http://192.168.151.18:3128 https://registry-1.docker.io/v2/

# 手动拉取镜像测试
docker pull --debug registry.cn-hangzhou.aliyuncs.com/library/alpine:latest
```

#### 2. pip安装包失败
```bash
# 测试代理连接
curl -v --proxy http://192.168.151.18:3128 https://pypi.org/simple/

# 使用国内源安装
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple package_name
```

#### 3. Git操作失败
```bash
# 测试Git代理
git config --global --get http.proxy
git config --global --get https.proxy

# 临时取消代理测试
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### 网络测试命令
```bash
# 测试代理服务器连通性
telnet 192.168.151.18 3128

# 通过代理访问外网
curl -v --proxy http://192.168.151.18:3128 https://www.google.com

# 测试Docker Hub访问
curl -v --proxy http://192.168.151.18:3128 https://index.docker.io/v1/
```

## 📋 环境检查清单

开发人员在开始开发前需要确认：

- [ ] 系统环境变量已配置 `HTTP_PROXY` 和 `HTTPS_PROXY`
- [ ] Git代理配置正确
- [ ] pip/conda使用国内镜像源
- [ ] Docker daemon配置了国内镜像加速和代理
- [ ] npm/yarn配置了国内镜像源
- [ ] 项目代码中的HTTP请求支持代理配置
- [ ] 外部API调用能够正常通过代理访问

## 🚀 快速配置脚本

创建自动化配置脚本 `scripts/setup-proxy.sh`：

```bash
#!/bin/bash
PROXY="http://192.168.151.18:3128"

# 设置系统环境变量
export HTTP_PROXY=$PROXY
export HTTPS_PROXY=$PROXY
export NO_PROXY="localhost,127.0.0.1,0.0.0.0,192.168.,10.,172.16."

# 配置pip
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
proxy = $PROXY
EOF

# 配置Docker
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null << EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ],
  "proxies": {
    "http-proxy": "$PROXY",
    "https-proxy": "$PROXY"
  }
}
EOF

# 重启Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# 配置Git
git config --global http.proxy $PROXY
git config --global https.proxy $PROXY

echo "代理配置完成！"
```

## 📚 参考资料

- [清华大学开源软件镜像站](https://mirrors.tuna.tsinghua.edu.cn/)
- [阿里云Docker镜像加速器](https://cr.console.aliyun.com/cn-hangzhou/mirrors)
- [中科大Docker镜像源](https://docker.mirrors.ustc.edu.cn/)
- [npm淘宝镜像源](https://registry.npmmirror.com/)