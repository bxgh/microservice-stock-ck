# 代码同步验证报告

**验证时间**: 2026-01-07 22:55  
**验证范围**: 3 台服务器 + 2 个远程仓库

---

## 1. Server 41 (192.168.151.41) ✅

### Git 配置
```
远程仓库:
  - origin  → https://gitee.com/wwsa518/microservice-stock.git
  - gitlab  → http://192.168.151.58:8800/root/microservice-stock.git

当前分支: feature/quant-strategy
追踪分支: gitlab/feature/quant-strategy
```

### 环境配置
```bash
SHARD_INDEX=0          # ✅ 已创建
SHARD_TOTAL=3
CLICKHOUSE_HOST=localhost
MOOTDX_API_URL=http://localhost:8003
TDX_POOL_SIZE=3
```

### 状态
- ✅ 双远程仓库配置正确
- ✅ 分支追踪 GitLab
- ✅ .env 文件已创建
- ✅ 工作目录干净

---

## 2. Server 58 (192.168.151.58)

### 预期配置
```bash
# Git 远程
origin  → https://gitee.com/wwsa518/microservice-stock.git (或无)
gitlab  → http://192.168.151.58:8800/root/microservice-stock.git

# 环境变量
SHARD_INDEX=1          # 关键差异
SHARD_TOTAL=3
```

### 验证项
- [ ] Git 远程指向 GitLab
- [ ] .env 文件存在且 SHARD_INDEX=1
- [ ] 当前分支为 feature/quant-strategy
- [ ] 代码与 GitLab 同步

---

## 3. Server 111 (192.168.151.111)

### 预期配置
```bash
# Git 远程
origin  → https://gitee.com/wwsa518/microservice-stock.git (或无)
gitlab  → http://192.168.151.58:8800/root/microservice-stock.git

# 环境变量
SHARD_INDEX=2          # 关键差异
SHARD_TOTAL=3
```

### 验证项
- [ ] Git 远程指向 GitLab
- [ ] .env 文件存在且 SHARD_INDEX=2
- [ ] 当前分支为 feature/quant-strategy
- [ ] 代码与 GitLab 同步

---

## 4. 远程仓库同步状态

### Gitee (origin)
```
URL: https://gitee.com/wwsa518/microservice-stock.git
用途: 外部备份、公开分享
```

**验证命令**:
```bash
git log origin/feature/quant-strategy --oneline -5
```

### GitLab (gitlab)
```
URL: http://192.168.151.58:8800/root/microservice-stock.git
用途: 内网 CI/CD、集群部署
```

**验证命令**:
```bash
git log gitlab/feature/quant-strategy --oneline -5
```

**同步检查**:
```bash
# 检查两个远程是否同步
git log origin/feature/quant-strategy..gitlab/feature/quant-strategy
# 预期: 无输出 (表示同步)
```

---

## 5. 关键文件检查清单

| 文件 | Server 41 | Server 58 | Server 111 |
|------|-----------|-----------|------------|
| `.env` | ✅ (SHARD=0) | ⏳ 待验证 | ⏳ 待验证 |
| `docs/epics/EPIC_016_*.md` | ✅ | ⏳ | ⏳ |
| `docs/operations/CODE_SYNC_STRATEGY.md` | ✅ | ⏳ | ⏳ |
| `services/gsd-worker/src/jobs/sync_tick.py` | ✅ | ⏳ | ⏳ |
| `services/mootdx-api/src/core/tdx_pool.py` | ✅ | ⏳ | ⏳ |

---

## 6. 手动验证步骤

### 在 Server 58 执行
```bash
cd /home/bxgh/microservice-stock
git remote -v
git branch -vv
cat .env | grep SHARD_INDEX
# 预期输出: SHARD_INDEX=1
```

### 在 Server 111 执行
```bash
cd /home/bxgh/microservice-stock
git remote -v
git branch -vv
cat .env | grep SHARD_INDEX
# 预期输出: SHARD_INDEX=2
```

### 检查远程仓库同步
```bash
# 在 Server 41 执行
cd /home/bxgh/microservice-stock
git fetch origin
git fetch gitlab
git log --oneline --graph --all --decorate -10
```

---

## 7. 验证结果汇总

### Server 41 ✅
- Git 配置: ✅ 正确
- .env 文件: ✅ 已创建 (SHARD_INDEX=0)
- 代码状态: ✅ 干净

### Server 58 ⏳
- 需要手动验证 SHARD_INDEX=1

### Server 111 ⏳
- 需要手动验证 SHARD_INDEX=2

### 远程仓库 ⏳
- Gitee: 需要验证最新提交
- GitLab: 需要验证最新提交

---

## 8. 下一步行动

1. **验证 Server 58/111**: 执行上述手动验证命令
2. **确认远程同步**: 检查 Gitee 和 GitLab 的最新提交是否一致
3. **测试分片采集**: 在各服务器测试 `--shard-index` 参数

---

*验证报告生成时间: 2026-01-07 22:55*
