FROM python:3.10-slim

# 安装 Node.js (pywencai 依赖)
RUN apt-get update && apt-get install -y \
    nodejs npm curl \
    && rm -rf /var/lib/apt/lists/*

# 验证 Node.js 安装
RUN node --version && npm --version

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制共享库
COPY ../../libs/common /app/libs/common

# 复制源码
COPY src/ /app/src/

# 设置 Python 路径
ENV PYTHONPATH=/app:/app/libs/common

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import grpc; from datasource.v1 import data_source_pb2_grpc, data_source_pb2; \
    channel = grpc.insecure_channel('localhost:50053'); \
    stub = data_source_pb2_grpc.DataSourceServiceStub(channel); \
    stub.HealthCheck(data_source_pb2.Empty(), timeout=5.0)" || exit 1

# 启动服务
CMD ["python", "src/main.py"]
