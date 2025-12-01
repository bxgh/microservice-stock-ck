# Story 004.01: 初始股票池管理（沪深300 Top 100）

**Epic**: EPIC-004 股票池动态管理  
**优先级**: P1  
**预估工期**: 2 天  
**状态**: 📝 待开始

---

## 📋 Story 描述

**作为** 系统工程师  
**我希望** 系统能从100只高流动性股票开始采集  
**以便** 验证系统稳定性和资源承载能力

---

## 🎯 验收标准

### 功能需求
- [ ] 自动获取沪深300成分股并按成交额排序Top 100（来源：akshare）
- [ ] L1 池初始规模固定为 100 只
- [ ] 3秒/轮的高频采集策略
- [ ] 支持手动配置股票列表（应急备选）

### 性能需求
- [ ] 股票池加载时间 < 5 秒
- [ ] 成分股更新失败时能使用缓存降级
- [ ] 支持每日自动更新股票池（考虑调仓）

### 测试需求
- [ ] 单元测试覆盖率 > 90%
- [ ] 集成测试验证 akshare API 调用
- [ ] 异常场景测试（API失败、网络超时等）

---

## 🔧 技术设计

### 1. 股票池数据获取

```python
# src/services/stock_pool/pool_initializer.py
import akshare as ak
from typing import List
from datetime import datetime

class StockPoolInitializer:
    """初始股票池管理器"""
    
    def __init__(self, cache_path: str = "cache/stock_pools"):
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
    
    async def get_hs300_top100(self) -> List[str]:
        """获取沪深300成分股按成交额Top 100"""
        try:
            # 1. 获取沪深300成分股
            df_cons = ak.index_stock_cons(symbol="000300")
            
            # 2. 获取最近5日平均成交额
            stock_volumes = []
            for code in df_cons["品种代码"].tolist():
                try:
                    df_daily = ak.stock_zh_a_hist(
                        symbol=code, 
                        period="daily", 
                        start_date=(datetime.now() - timedelta(days=7)).strftime("%Y%m%d"),
                        end_date=datetime.now().strftime("%Y%m%d")
                    )
                    avg_amount = df_daily["成交额"].mean()
                    stock_volumes.append({
                        "code": code,
                        "name": df_cons[df_cons["品种代码"] == code]["品种名称"].iloc[0],
                        "avg_amount": avg_amount
                    })
                except Exception as e:
                    logger.warning(f"获取{code}成交额失败: {e}")
                    continue
            
            # 3. 排序并取Top 100
            sorted_stocks = sorted(
                stock_volumes, 
                key=lambda x: x["avg_amount"], 
                reverse=True
            )[:100]
            
            # 4. 保存到缓存
            await self._save_cache(sorted_stocks)
            
            return [s["code"] for s in sorted_stocks]
            
        except Exception as e:
            logger.error(f"获取沪深300 Top100失败: {e}")
            return await self._load_from_cache()
    
    async def _save_cache(self, stocks: List[dict]):
        """保存股票池到缓存"""
        cache_file = self.cache_path / f"hs300_top100_{datetime.now().date()}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "stocks": stocks
            }, f, ensure_ascii=False, indent=2)
    
    async def _load_from_cache(self) -> List[str]:
        """从缓存加载股票池（降级方案）"""
        cache_files = sorted(self.cache_path.glob("hs300_top100_*.json"), reverse=True)
        if not cache_files:
            raise ValueError("无可用缓存，请检查网络连接")
        
        with open(cache_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.warning(f"使用缓存数据（日期: {data['updated_at']}）")
            return [s["code"] for s in data["stocks"]]
```

### 2. 配置文件设计

```yaml
# config/stock_pools.yaml
version: "1.0.0"
updated_at: "2025-12-01T21:00:00+08:00"

# L1 核心池配置
L1_pool:
  enabled: true
  max_size: 100
  acquisition_interval: 3  # 秒
  
  # 数据源优先级
  data_sources:
    - type: "akshare_hs300_top100"
      enabled: true
      update_schedule: "0 8 * * *"  # 每天8点更新
    - type: "manual_config"
      enabled: false
      stock_list: []  # 手动配置股票列表
  
  # 降级策略
  fallback:
    use_cache: true
    max_cache_age_days: 7
    
# 黑名单（避免采集）
blacklist:
  patterns:
    - "ST*"      # ST股票
    - "*退*"     # 退市股票
  codes:
    - "600000"   # 示例：手动添加的黑名单股票
```

### 3. 集成到 AcquisitionScheduler

```python
# src/scheduler/acquisition_scheduler.py
from services.stock_pool.pool_initializer import StockPoolInitializer

class AcquisitionScheduler:
    def __init__(self):
        # ... 原有代码 ...
        self.pool_initializer = StockPoolInitializer()
        self.L1_pool: List[str] = []
    
    async def initialize(self):
        """初始化调度器"""
        # 1. 加载股票池
        self.L1_pool = await self.pool_initializer.get_hs300_top100()
        logger.info(f"L1股票池加载完成，共 {len(self.L1_pool)} 只股票")
        
        # 2. 启动定时更新任务
        asyncio.create_task(self._schedule_pool_update())
        
        # ... 原有初始化代码 ...
    
    async def _schedule_pool_update(self):
        """每日更新股票池"""
        while True:
            try:
                # 等待到每天8点
                await self._wait_until_time(hour=8, minute=0)
                
                # 更新股票池
                new_pool = await self.pool_initializer.get_hs300_top100()
                
                async with self._pool_lock:
                    old_count = len(self.L1_pool)
                    self.L1_pool = new_pool
                    logger.info(f"股票池已更新: {old_count} -> {len(new_pool)}")
                
            except Exception as e:
                logger.error(f"股票池更新失败: {e}")
                await asyncio.sleep(3600)  # 失败后1小时重试
```

---

## ✅ 测试计划

### 1. 单元测试

```python
# tests/test_stock_pool_initializer.py
import pytest
from services.stock_pool.pool_initializer import StockPoolInitializer

@pytest.mark.asyncio
async def test_get_hs300_top100_success():
    """测试成功获取沪深300 Top100"""
    initializer = StockPoolInitializer()
    stocks = await initializer.get_hs300_top100()
    
    assert len(stocks) == 100
    assert all(isinstance(code, str) for code in stocks)

@pytest.mark.asyncio
async def test_fallback_to_cache():
    """测试API失败时从缓存加载"""
    initializer = StockPoolInitializer()
    
    # Mock akshare API 失败
    with patch("akshare.index_stock_cons", side_effect=Exception("API Error")):
        stocks = await initializer.get_hs300_top100()
        assert len(stocks) > 0  # 应该从缓存加载
```

### 2. 集成测试

```bash
# 验证真实API调用
docker compose -f docker-compose.dev.yml run --rm get-stockdata \
    python -m scripts.test_stock_pool_init
```

---

## 📊 监控指标

- **股票池大小**: 实时 = 100 只（固定）
- **更新成功率**: > 95%（每日更新）
- **缓存命中率**: 记录 API 失败时的缓存使用情况
- **黑名单过滤数量**: 记录被过滤的股票数量

---

## 🚀 部署步骤

1. **创建配置文件**: `config/stock_pools.yaml`
2. **运行初始化脚本**: 验证能成功获取100只股票
3. **集成到 Scheduler**: 修改 `acquisition_scheduler.py`
4. **运行测试**: `pytest tests/test_stock_pool_initializer.py`
5. **观察1天**: 监控系统资源使用情况

---

## 📝 注意事项

1. **API限流**: akshare 调用频率不要过高，建议每次获取后 sleep 0.1秒
2. **缓存策略**: 缓存文件需定期清理，保留最近7天即可
3. **黑名单**: ST股票和退市股票必须过滤，避免数据质量问题
4. **时区**: 所有时间使用 `Asia/Shanghai`

---

**创建时间**: 2025-12-01  
**创建人**: AI 系统架构师  
**审核人**: 待定
