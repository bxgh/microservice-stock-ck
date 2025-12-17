# Pywencai Source - 使用与akshare-source相同的模式
FROM python:3.10-slim

# 构建参数
ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128

WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 配置apt代理和源 (Aliyun)
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    else \
        rm -f /etc/apt/apt.conf.d/00proxy; \
    fi

# 安装系统依赖 (包括proxychains4和nodejs)
RUN apt-get update && apt-get install -y \
    gcc curl proxychains4 nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# 配置 proxychains4
ARG PROXY_HOST=192.168.151.18
ARG PROXY_PORT=3128
RUN sed -i 's/^strict_chain/#strict_chain/' /etc/proxychains4.conf && \
    sed -i 's/^#dynamic_chain/dynamic_chain/' /etc/proxychains4.conf && \
    sed -i 's/^socks4.*127.0.0.1.*9050/#socks4 127.0.0.1 9050/' /etc/proxychains4.conf && \
    echo "http ${PROXY_HOST} ${PROXY_PORT}" >> /etc/proxychains4.conf

# 配置pip国内源 (Tencent)
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = https://mirrors.cloud.tencent.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.cloud.tencent.com' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf

# 复制依赖文件
COPY services/pywencai-source/requirements.txt /app/requirements.txt

# 安装 Python 依赖
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制共享库
COPY libs/common /app/libs/common
ENV PYTHONPATH=/app/libs/common:$PYTHONPATH

# 复制服务代码
COPY services/pywencai-source/src /app/src

# 复制entrypoint
COPY services/pywencai-source/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 环境变量
ENV SERVICE_NAME=pywencai-source
ENV SERVICE_PORT=50053

# 使用entrypoint配置运行时代理
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["python", "src/main.py"]
