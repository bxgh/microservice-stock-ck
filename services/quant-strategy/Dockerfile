# Quant Strategy 微服务 Dockerfile
FROM python:3.12-slim

# 设置代理环境变量
ENV http_proxy=http://192.168.151.18:3128 \
    https_proxy=http://192.168.151.18:3128 \
    HTTP_PROXY=http://192.168.151.18:3128 \
    HTTPS_PROXY=http://192.168.151.18:3128

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# 配置apt使用国内源和代理
RUN echo 'Acquire::http::Proxy "http://192.168.151.18:3128";' > /etc/apt/apt.conf.d/00proxy && \
    echo 'Acquire::https::Proxy "http://192.168.151.18:3128";' >> /etc/apt/apt.conf.d/00proxy && \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 配置pip使用国内源和代理
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = https://pypi.tuna.tsinghua.edu.cn/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = pypi.tuna.tsinghua.edu.cn' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf

# 升级pip (使用国内源)
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制完整依赖文件
COPY requirements.txt .

# 安装Python依赖 (优先使用国内源)
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || \
    pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple || \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.douban.com/simple/ || \
    pip install --no-cache-dir -r requirements.txt

# 复制FastAPI应用代码
COPY src/ ./src/
COPY config/ ./config/

# 创建非root用户和日志目录
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app/logs && \
    mkdir -p /app/data && \
    chown -R app:app /app

# 切换到非root用户
USER app

# 暴露端口
EXPOSE 8084

# 启动命令
CMD ["python", "src/main.py"]
