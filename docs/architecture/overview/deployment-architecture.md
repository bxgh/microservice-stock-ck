# Deployment Architecture

## Deployment Strategy

**Frontend Deployment:**
- **Platform:** Docker Container (Nginx)
- **Build Command:** `npm run build`
- **Output Directory:** `services/web-ui/dist`
- **CDN/Edge:** API Gateway serves static files with Nginx caching

**Backend Deployment:**
- **Platform:** Docker Containers (Python FastAPI)
- **Build Command:** Docker build from each service directory
- **Deployment Method:** Docker Compose with service orchestration
- **Load Balancing:** Nginx API Gateway with round-robin
- **Service Discovery:** Docker Compose internal network DNS

## Environments

| Environment | Frontend URL | Backend URL | Purpose |
|-------------|--------------|-------------|---------|
| Development | http://localhost:3000 | http://localhost:8080 | 本地开发和测试 |
| Staging | http://staging.local:3000 | http://staging.local:8080 | 预生产测试环境 |
| Production | http://microservice-stock.local:3000 | http://microservice-stock.local:8080 | 生产环境 |

## Production Docker Compose Configuration

```yaml
# infrastructure/docker-compose.prod.yml
version: '3.8'

services:
  # 基础设施
  redis:
    image: redis:7.0-alpine
    container_name: microservice-stock-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf
    ports:
      - "6379:6379"
    networks:
      - microservice-stock

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: microservice-stock-clickhouse
    restart: unless-stopped
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - ./clickhouse/config.xml:/etc/clickhouse-server/config.xml
    ports:
      - "8123:8123"
      - "9000:9000"
    networks:
      - microservice-stock

  # 应用服务
  task-scheduler:
    image: microservice-stock/task-scheduler:latest
    container_name: microservice-stock-task-scheduler
    restart: unless-stopped
    environment:
      - MYSQL_HOST=${MYSQL_HOST}
      - REDIS_HOST=redis
      - CLICKHOUSE_HOST=clickhouse
      - LOG_LEVEL=INFO
    ports:
      - "8001:8001"
    volumes:
      - ./logs/task-scheduler:/app/logs
    networks:
      - microservice-stock
    depends_on:
      - redis
      - clickhouse

  # API Gateway
  api-gateway:
    image: microservice-stock/api-gateway:latest
    container_name: microservice-stock-api-gateway
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./logs/nginx:/var/log/nginx
    networks:
      - microservice-stock
    depends_on:
      - task-scheduler

volumes:
  redis_data:
    driver: local
  clickhouse_data:
    driver: local

networks:
  microservice-stock:
    driver: bridge
```
