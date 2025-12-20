FROM python:3.12-slim

# 构建参数
ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128

# 配置apt代理
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy; \
    fi

WORKDIR /app

COPY requirements.txt .

# 使用腾讯云镜像并配置超时
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = http://mirrors.cloud.tencent.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.cloud.tencent.com' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf

RUN pip install --no-cache-dir -r requirements.txt

COPY akshare_api.py .

EXPOSE 8000

CMD ["python", "akshare_api.py"]
