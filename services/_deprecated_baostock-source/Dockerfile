# Baostock Source Service
FROM python:3.12-slim

WORKDIR /app

ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128

# Set timezone
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Configure apt proxy
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    else \
        rm -f /etc/apt/apt.conf.d/00proxy; \
    fi

# Install system dependencies
# proxychains4 is critical for connecting to baostock port 10030 via SOCKS5
RUN apt-get update && apt-get install -y \
    gcc curl proxychains4 \
    && rm -rf /var/lib/apt/lists/*

# Configure proxychains4 template (will be updated by entrypoint)
# We default to strict_chain to force SOCKS5 usage
RUN sed -i 's/^strict_chain/strict_chain/' /etc/proxychains4.conf && \
    sed -i 's/^dynamic_chain/#dynamic_chain/' /etc/proxychains4.conf && \
    sed -i 's/^socks4 127.0.0.1 9050/#socks4 127.0.0.1 9050/' /etc/proxychains4.conf

# Configure PIP mirror (Use HTTP to avoid proxy CONNECT restrictions)
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = http://mirrors.aliyun.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.aliyun.com' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf

# Copy requirements and install
COPY services/baostock-source/requirements.txt /app/requirements.txt
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL \
        pip install --no-cache-dir -r /app/requirements.txt; \
    else \
        pip install --no-cache-dir -r /app/requirements.txt; \
    fi

# Copy shared libs
COPY libs/common /app/libs/common
ENV PYTHONPATH=/app/libs/common:$PYTHONPATH

# Copy source code
COPY services/baostock-source/src /app/src

# Copy entrypoint
COPY services/baostock-source/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Environment variables
ENV SERVICE_NAME=baostock-source
ENV SERVICE_PORT=50054

# Use entrypoint to configure proxychains
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["python", "src/main.py"]
