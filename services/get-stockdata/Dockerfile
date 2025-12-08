# Get Stock Data 微服务 - 应用镜像
# 基于预构建的基础镜像，只包含应用代码
FROM get-stockdata-base:latest

# 设置PYTHONPATH
ENV PYTHONPATH=/app/src

# 复制应用代码和配置
COPY src/ ./src/
COPY config/ ./config/
COPY entrypoint.sh /app/entrypoint.sh

# 设置权限
RUN chmod +x /app/entrypoint.sh && \
    chown -R app:app /app/src /app/config /app/entrypoint.sh

# 切换到非root用户
USER app

# 暴露端口
EXPOSE 8086

# 使用entrypoint配置运行时代理
ENTRYPOINT ["/app/entrypoint.sh"]

# 启动命令
CMD ["python", "src/main.py"]