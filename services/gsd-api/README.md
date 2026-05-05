# GSD-API

股票数据查询服务 - 只读API

## 功能

- 实时行情查询
- K线数据查询
- 市场数据查询
- 股票列表查询
- 财务数据查询

## 运行

```bash
# 开发模式
cd services/gsd-api
pip install -e ../../libs/gsd-shared
pip install -r requirements.txt
python src/main.py

# Docker模式
docker build -t gsd-api .
docker run -p 8000:8000 gsd-api
```

## API文档

访问 http://localhost:8000/docs

## 依赖

- gsd-shared (共享数据模型)
- ClickHouse (数据存储)
- Redis (缓存)
