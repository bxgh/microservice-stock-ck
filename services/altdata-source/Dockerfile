FROM python:3.12-slim

WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    TZ=Asia/Shanghai

# 安装基础工具及时区数据
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    tzdata \\
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

# 复制依赖定义
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制源码
COPY . .

# 暴露端口，注意与配置的一致 (8011)
EXPOSE 8011

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8011", "--forwarded-allow-ips", "*"]
