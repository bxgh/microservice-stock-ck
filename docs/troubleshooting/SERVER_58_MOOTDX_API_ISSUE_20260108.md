# Server 58 mootdx-api 股票列表问题

**报告时间**: 2026-01-08 18:22  
**服务器**: 192.168.151.58  
**问题类型**: mootdx-api `/api/v1/stocks` 接口返回空数据  
**影响范围**: 无法进行分布式分笔数据采集（Shard 1）

---

## 问题现象

### API 层面
```bash
curl http://localhost:8003/api/v1/stocks
# 返回: []
```

### mootdx 库层面
```bash
docker exec microservice-stock-mootdx-api python -c '
from mootdx.quotes import Quotes
q = Quotes.factory(market="std")
stocks = q.stocks(market=1)
print(f"Market 1: {len(stocks)} stocks")
'
# 返回: Market 1: 26460 stocks
```

---

## 根本原因

**FastAPI 应用层的股票列表缓存/初始化问题**

- mootdx 底层库工作正常（能获取 26,460 只股票）
- FastAPI `/api/v1/stocks` 接口返回空数组
- 服务健康检查显示 `healthy`
- 分笔数据查询接口 `/api/v1/tick/{code}` 工作正常

可能原因：
1. TDX 连接池初始化时，股票列表未正确加载
2. 股票列表缓存机制有 bug
3. API 路由处理逻辑问题

---

## 临时解决方案

### 方案 1: 重启服务（已尝试，无效）
```bash
docker restart microservice-stock-mootdx-api
# 结果: 仍返回空数组
```

### 方案 2: 重建容器（已尝试，无效）
```bash
docker stop microservice-stock-mootdx-api
docker rm microservice-stock-mootdx-api
docker run -d --name microservice-stock-mootdx-api \
  --restart always --network host \
  -e TDX_POOL_SIZE=3 \
  microservice-stock-mootdx-api:latest
# 结果: 仍返回空数组
```

---

## 代码层面排查

需要检查 `services/mootdx-api/src/api/routes.py` 中的 `/api/v1/stocks` 端点：

```python
@router.get("/stocks")
async def get_stocks(market: Optional[int] = None):
    # 检查这里的逻辑
    # 可能的问题:
    # 1. handler.get_stocks() 返回空
    # 2. 缓存未正确初始化
    # 3. TDX 连接池状态问题
    pass
```

### 建议修复方向

1. **添加日志**: 在 `get_stocks()` 方法中添加详细日志
2. **检查缓存**: 确认股票列表缓存机制
3. **初始化顺序**: 确保 TDX 连接池初始化后才加载股票列表
4. **添加刷新接口**: 提供 `/api/v1/stocks/refresh` 端点手动刷新

---

## 影响评估

### 当前影响
- ❌ Server 58 无法参与分布式采集
- ✅ Server 41 和 111 正常工作（2 节点并行）
- ✅ 分笔数据查询功能正常（其他服务器可以使用 Server 58 的 tick API）

### 业务影响
- **中等影响**: 3 节点降级为 2 节点
- **性能影响**: 采集时间从预期 27 分钟增加到约 40 分钟
- **数据完整性**: 无影响（Server 41 + 111 覆盖全部股票）

---

## 后续行动

### 短期（P1）
1. 完成当前 2 节点测试
2. 分析 mootdx-api 代码逻辑
3. 添加详细日志和调试信息

### 中期（P2）
1. 修复股票列表接口 bug
2. 添加股票列表刷新机制
3. 增强健康检查（包含股票列表状态）

### 长期（P3）
1. 重构 mootdx-api 初始化流程
2. 添加自动恢复机制
3. 实现股票列表定时刷新

---

## 相关日志

### mootdx-api 日志（最后 30 行）
```
INFO:     127.0.0.1:37052 - "GET /api/v1/tick/300199?date=20260107&start=0&offset=800 HTTP/1.1" 200 OK
INFO:     127.0.0.1:51836 - "GET /api/v1/tick/300317?date=20260107&start=0&offset=800 HTTP/1.1" 200 OK
...
（分笔数据查询正常工作）
```

### 健康检查
```json
{
  "status": "healthy",
  "service": "mootdx-api"
}
```

---

*文档生成时间: 2026-01-08 18:22*  
*优先级: P1 (中等)*  
*状态: 待修复*
