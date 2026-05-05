# Story 8.2: 云服务 - Baostock API

**Epic**: [EPIC-008 混合数据源架构](./EPIC-008-混合架构实施.md)  
**状态**: 就绪  
**优先级**: P0 (关键路径)  
**工作量**: 2天  
**负责人**: 待定

---

## Story 描述

**作为** 数据分析师  
**我想要** 从1990年至今的历史K线数据  
**以便** 进行长期趋势分析和回测

---

## 目标

1. 为 baostock 库创建 FastAPI 封装
2. 实现会话超时的自动重连逻辑
3. 使用 Docker 部署到腾讯云 (124.221.80.250)
4. 配置 systemd 实现自动重启

---

## 技术设计

### API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/history/kline/{symbol}` | 历史K线数据 |
| GET | `/api/v1/index/cons/{index_code}` | 指数成分股 |
| GET | `/api/v1/industry/classify` | 行业分类 |

### 请求/响应示例

**请求:**
```http
GET /api/v1/history/kline/600519?start_date=2024-01-01&end_date=2024-12-31&frequency=d&adjust=2
```

**响应:**
```json
[
  {
    "date": "2024-01-02",
    "open": "1720.00",
    "high": "1745.00",
    "low": "1715.00",
    "close": "1738.00",
   "volume": "3500000",
    "amount": "6065000000",
    "pctChg": "1.05",
    "turn": "0.28"
  }
]
```

---

## 验收标准

### 功能性

- [ ] `/health` 端点在登录后返回 `{"status": "healthy"}`
- [ ] 历史K线 API 返回 SH600519 的数据 (2024-01-01 to 2024-12-31)
- [ ] 指数成分股 API 返回沪深300股票
- [ ] 行业分类 API 返回有效结果

### 非功能性

- [ ] 200个数据点的响应时间 < 500ms (p95)
- [ ] 服务崩溃时自动重启 (systemd 配置)
- [ ] 日志写入 `/var/log/baostock-api.log`
- [ ] Docker 容器健康检查通过

---

## 实施步骤

### 1. 创建 API 应用

参考已生成的 `cloud-deploy/baostock-api/baostock_api.py`

### 2. 创建 Dockerfile

参考已生成的 `cloud-deploy/baostock-api/Dockerfile`

### 3. 部署到云端

```bash
# 在腾讯云服务器上
scp -r cloud-deploy ubuntu@124.221.80.250:/opt/
ssh ubuntu@124.221.80.250
cd /opt/cloud-deploy
docker-compose up -d baostock-api
```

---

## 测试策略

### 手动验证

```bash
# 从本地机器
curl -x http://192.168.151.18:3128 \
  "http://124.221.80.250:8001/api/v1/history/kline/600519?start_date=2024-01-01&end_date=2024-12-31"
```

---

## 依赖关系

### 外部
- [ ] 腾讯云服务器 SSH 访问
- [ ] 云端安装 Docker 和 Docker Compose
- [ ] 防火墙允许 8001 端口

### 内部
- [ ] Story 8.1 完成（本地容器可以调用此 API）

---

## 风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Baostock 会话超时 (30分钟) | 中 | 每次查询前实施自动重连 |
| 端口 8001 被防火墙阻止 | 高 | 配置 `ufw allow 8001/tcp` |

---

## 完成定义

- [ ] API 部署并可在 `http://124.221.80.250:8001` 访问
- [ ] 健康检查返回 200
- [ ] 手动测试: 成功检索历史K线数据
- [ ] Docker 日志 24小时内无错误
- [ ] Systemd/Docker 重启策略已验证
