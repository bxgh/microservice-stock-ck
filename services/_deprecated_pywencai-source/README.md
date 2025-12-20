# Pywencai Source Microservice

基于 pywencai 的数据源微服务，提供自然语言查询能力。

## 功能

- **SCREENING (选股)**: 自然语言选股，如"今日涨停股票"
- **RANKING (榜单)**: 各类排行榜数据  
- **SECTOR (板块)**: 行业/概念涨幅榜

## 技术栈

- Python 3.10
- Node.js v16+ (pywencai 依赖)
- gRPC
- Nacos (服务注册)

## 环境变量

```bash
SERVICE_NAME=pywencai-source
SERVICE_PORT=50053
SERVICE_HOST=127.0.0.1
NACOS_SERVER_ADDR=127.0.0.1:8848
LOG_LEVEL=INFO
```

## 本地开发

```bash
# 构建镜像
docker build -t pywencai-source:latest .

# 运行服务
docker run --network host \
  -e SERVICE_PORT=50053 \
  -e NACOS_SERVER_ADDR=127.0.0.1:8848 \
  pywencai-source:latest
```

## 健康检查

```python
import grpc
from datasource.v1 import data_source_pb2_grpc, data_source_pb2

channel = grpc.insecure_channel('localhost:50053')
stub = data_source_pb2_grpc.DataSourceServiceStub(channel)
response = stub.HealthCheck(data_source_pb2.Empty())
print(response.healthy, response.message)
```

## 特性

### 缓存机制
- TTL: 5分钟
- 最大缓存: 100 条查询
- LRU 淘汰策略

### 性能
- 查询延迟: 5-15秒
- 并发支持: 10 workers
- 超时设置: 30秒

## 注意事项

⚠️ **验证码风险**: pywencai 可能需要处理验证码，导致查询失败。建议实现降级机制。

⚠️ **Node.js 依赖**: 服务依赖 Node.js 环境，镜像体积较大 (~200MB)。
