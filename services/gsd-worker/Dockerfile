FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 gsd-shared
COPY ../../libs/gsd-shared /tmp/gsd-shared
RUN pip install -e /tmp/gsd-shared

# 复制源代码
COPY src/ ./src/

# 默认执行同步任务
ENTRYPOINT ["python", "-m"]
CMD ["jobs.sync_kline"]
