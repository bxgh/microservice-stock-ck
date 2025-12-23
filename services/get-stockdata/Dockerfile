# Get Stock Data Service - Application Image
FROM get-stockdata-base:latest

# 设置工作目录
WORKDIR /app

# 设置PYTHONPATH
ENV PYTHONPATH=/app/src

# 复制应用代码和配置
COPY src/ ./src/
COPY config/ ./config/
COPY entrypoint.sh /app/entrypoint.sh
COPY tests/ ./tests/

# 设置权限 (base image already has 'app' user)
USER root
RUN chmod +x /app/entrypoint.sh && \
    chown -R app:app /app/src /app/config /app/entrypoint.sh /app/tests

# 切换到非root用户
USER app

# 暴露端口 (内部端口 8083)
EXPOSE 8083

# 🚀 启动命令
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "src/main.py"]