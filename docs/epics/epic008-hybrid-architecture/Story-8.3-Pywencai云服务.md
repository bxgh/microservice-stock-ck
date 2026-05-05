# Story 8.3: 云服务 - Pywencai API

**Epic**: [EPIC-008 混合数据源架构](./EPIC-008-混合架构实施.md)  
**状态**: 就绪  
**优先级**: P1 (高)  
**工作量**: 2天  
**负责人**: 待定

---

## Story 描述

**作为** 量化研究员  
**我想要** 使用自然语言查询筛选股票  
**以便** 无需复杂SQL查询就能快速识别投资机会

---

## 目标

1. 为 pywencai 库创建 FastAPI 封装
2. 在腾讯云上安装 Node.js 依赖
3. 实现查询缓存以减少 API 调用
4. 使用 Docker 部署 (端口 8002)

---

## 技术设计

### API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/query` | 自然语言查询 |
| GET | `/api/v1/screening/limit_up` | 今日涨停股票 |
| GET | `/api/v1/screening/continuous_limit_up` | 连续涨停 (N天) |
| GET | `/api/v1/sector/industry` | 行业表现排名 |
| GET | `/api/v1/sector/concept` | 概念板块表现排名 |

### 请求/响应示例

**请求:**
```http
GET /api/v1/query?q=今日涨停股票&perpage=20
```

**响应:**
```json
{
  "data": [
    {"code": "000001", "name": "平安银行", "pct_chg": "10.02%"},
    {"code": "600519", "name": "贵州茅台", "pct_chg": "10.01%"}
  ],
  "cached": false
}
```

---

## 验收标准

### 功能性

- [ ] 自然语言查询 "今日涨停" 返回有效股票列表
- [ ] 缓存将重复查询延迟减少 >80%
- [ ] 优雅处理验证码错误 (返回 429 状态 + retry-after 头)
- [ ] 支持至少 4个预设查询端点

### 非功能性

- [ ] 未缓存查询响应时间 < 3s (p95)
- [ ] 缓存查询响应时间 < 50ms (p95)
- [ ] 云端安装 Node.js v18+
- [ ] Docker 健康检查通过

---

## 实施步骤

### 1. 在云端安装 Node.js

```bash
# 在腾讯云服务器上
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证
node --version  # 应该是 v18.x 或更高
```

### 2. 创建 API 应用

参考已生成的 `cloud-deploy/pywencai-api/pywencai_api.py`

### 3. 创建 Dockerfile

参考 Story 8.2 中 pywencai-api 的 Dockerfile 模板

---

## 测试策略

### 手动验证

```bash
# 从本地机器
curl -x http://192.168.151.18:3128 \
  "http://124.221.80.250:8002/api/v1/query?q=今日涨停股票"
```

---

## 依赖关系

### 外部
- [ ] 腾讯云上安装 Node.js v18+
- [ ] 防火墙允许 8002 端口

### 内部
- [ ] Story 8.1 完成 (本地容器可以调用此 API)

---

## 风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 频繁查询触发验证码 | 高 | 实施 5分钟退避，积极缓存 |
| Node.js 依赖冲突 | 中 | 使用预装 Node 的 Docker 镜像 |
| Pywencai API 变更 | 中 | 固定 pywencai 版本，添加集成测试 |

---

## 完成定义

- [ ] API 部署在 `http://124.221.80.250:8002`
- [ ] 健康检查返回 200
- [ ] 手动测试: "今日涨停" 查询返回结果
- [ ] 缓存已验证 (第二次相同查询 < 50ms)
- [ ] 验证码错误优雅处理 (429 状态)
