FROM alpine:latest

# 安装必要的工具
RUN apk add --no-cache docker-cli

# 复制清理脚本
COPY docker-cleanup.sh /usr/local/bin/docker-cleanup.sh
RUN chmod +x /usr/local/bin/docker-cleanup.sh

# 安装 cron
RUN apk add --no-cache crontabs

# 添加 crontab 任务
RUN echo '0 2 * * * /usr/local/bin/docker-cleanup.sh' >> /etc/crontabs/root

# 启动脚本
CMD echo "启动 Docker 定时清理容器..." && crond -f -l 2