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

# 注意: pywencai 理论上需要 Node.js v16+ 环境
# 如果测试发现必须有Node.js，可以后续添加
# 先用纯Python环境测试

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

# 环境变量
ENV SERVICE_NAME=pywencai-source
ENV SERVICE_PORT=50053

CMD ["python", "src/main.py"]
