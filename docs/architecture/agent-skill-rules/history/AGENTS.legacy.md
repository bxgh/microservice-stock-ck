# AGENTS.md (Legacy Version - Pre-E102 Refactor)
> 此文件为 2026-05-09 重构前的历史版本，仅供追溯具体的字段映射和量纲细节。
> 生产开发请以根目录下的最新 AGENTS.md 及自动化工具链为准。

---

## 3. 命名规范(强制)

### 3.1 表前缀
| 前缀 | 用途 | 写入方 | 关键约定 |
|---|---|---|---|
| `ods_` | 原始数据层 | 云端采集 | **永不修改**,只能 TRUNCATE 重灌 |
| `dwd_` | 明细层 | 本仓 | 清洗 / 脱敏后明细 |
| `dim_` | 维度表 | 手工 / 批量 | 字典 / 基础信息 |
| `ads_` | 应用数据层 | 本仓 | 每日聚合指标 |
| `app_` | 应用面表 | 本仓 | 前端直查专用 |
| `obs_` | 观察点系统 | 本仓 | 第 9 章专属 |
| `train_` | 认知训练系统 | 用户 / 本仓 | 第 8 章专属 |
| `meta_` | 系统元数据 | 系统 | 调度 / 契约 |

### 3.2 字段命名
| 必须用 | 不要用 |
|---|---|
| `ts_code` (VARCHAR(20)) | `stock_code` / `code` |
| `symbol` (VARCHAR(10)) | (symbol 专指纯数字代码) |
| `trade_date` (DATE) | `dt` / `date` / `t_date` |
| `pct_chg` (DECIMAL(10,6)) | `pct` / `change_pct` / `chg` |
| `amount` (DECIMAL(20,2)) | `vol` / `volume` (成交额/成交量) |
| `volume` (BIGINT) | 成交量 (股) |
| `created_at` / `updated_at` | `ctime` / `mtime` / `create_time` |
| `is_deleted` (TINYINT(1)) | `deleted` / `is_del` |

### 3.3 表结构三件套
```sql
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
is_deleted TINYINT(1) NOT NULL DEFAULT 0,
KEY idx_updated_at (updated_at)
```

## 4. 单位陷阱
| 字段 | 入库规范 | 上游格式 | 强制处理 |
|---|---|---|---|
| `pct_chg` | 小数 | 通常已是小数 | 采集层 sanity check |
| ETF `share_chg` | 亿份 | 直接存 | 净申购金额 = share_chg * nav * 1e8 |
| `amount`(成交额) | 元 | Tushare 千元 / akshare 元 | 各源单独适配,统一为元 |

... (其余内容已在最新 AGENTS.md 中保留)
