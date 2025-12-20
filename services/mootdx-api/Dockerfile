FROM python:3.12-slim

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 设置 Python 路径
ENV PYTHONPATH=/app/src

# 健康检查 (使用 Python)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')"

# 暴露端口
EXPOSE 8003

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
