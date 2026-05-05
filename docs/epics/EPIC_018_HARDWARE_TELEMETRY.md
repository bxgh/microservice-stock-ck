# EPIC-018: 硬件算力穿透 (Hardware Telemetry)

## Epic 概述

| 字段 | 值 |
|------|-----|
| **Epic ID** | EPIC-018 |
| **标题** | 硬件算力穿透 (Hardware Telemetry Strategy) |
| **优先级** | P1 |
| **状态** | 🏗️ 规划中 |
| **创建日期** | 2026-02-28 |
| **项目** | [GPU 产业链另类数据](../design/GPU.md) |

---

## 1. 目标
通过监控本土 AI 算力的物理供给与资本投入平衡，捕捉算力周期波动。

### 核心指标
1.  **算力时价 (Spot Price)**: 监控 A100/H800 与 昇腾910B/海光DCU 的二手/现货市场价格趋势。
2.  **算力溢价剪刀差**: 国内外算力资源性价比的偏离值。
3.  **物理 CAPEX**: 招投标市场的真金白银投入额。

---

## 2. 用户故事 (Stories)

### Story 18.1: 现货算力行情采集 (Cloud GPU Spot)
**目标**: 采集阿里云、腾讯云、AutoDL 等平台的 GPU 实例价格。
- [ ] 调研 AutoDL/阿里云 PAI 的开放 API 或价格页面。
- [ ] 在 `altdata-source` 中实现 `HardwareMarketCollector`。
- [ ] 存储至 `altdata.hardware_spot_prices` 表。

### Story 18.2: 政企招投标数据抽取 (Procurement NLP)
**目标**: 监控政府采购网，提取 AI 硬件相关标讯。
- [ ] 实现针对招投标公告的采集器 (聚焦关键字：算力中心、GPU、华为昇腾)。
- [ ] 实现轻量级正则/模型提取 `(Entity, Amount)`。
- [ ] 存储至 `altdata.hardware_procurement_capex` 表。

### Story 18.3: 硬件信号生成与注入
**目标**: 计算 "算力溢价" 与 "CAPEX 爆发" 信号，注入 `quant-strategy`。
- [ ] 实现 `HardwareSignalStrategy`。
- [ ] 注入 `CandidatePoolService` (影响：服务器、算力租赁、国产算力芯片板块)。

---

## 3. 存储设计
- `altdata.hardware_spot_prices`: (timestamp, platform, instance_type, gpu_model, price_per_hour, availability)
- `altdata.hardware_procurement_capex`: (date, title, purchaser, hardware_type, amount, region)
