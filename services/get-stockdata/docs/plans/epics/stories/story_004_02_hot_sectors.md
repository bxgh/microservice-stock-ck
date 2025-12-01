# Story 004.02: 热门赛道股票池配置

**Epic**: EPIC-004 股票池动态管理  
**优先级**: P1  
**预估工期**: 3 天  
**状态**: 📝 待开始  
**前置依赖**: Story 004.01

---

## 📋 Story 描述

**作为** 量化研究员  
**我希望** 系统支持切换到热门赛道精选股票池（100只）  
**以便** 提高数据的商业价值和策略适配性

---

## 🎯 验收标准

### 功能需求
- [ ] 实现5大赛道分组配置（科技芯片、新能源、医药、消费、金融周期）
- [ ] 每个赛道15-20只龙头股票，共90只
- [ ] 预留10只动态妖股池（基于涨幅/换手率自动更新）
- [ ] 支持每周自动更新赛道成分股

### 赛道定义
- [ ] **科技芯片**（20只）：科创50 + 芯片ETF成分股
- [ ] **新能源**（20只）：新能源车ETF + 光伏ETF成分股
- [ ] **医药生物**（20只）：生物医药ETF + 创新药指数
- [ ] **消费白酒**（15只）：白酒ETF + 消费龙头
- [ ] **金融周期**（15只）：券商 + 银行 + 有色金融
- [ ] **超级妖股**（10只）：动态计算，每周更新

### 测试需求
- [ ] 单元测试覆盖率 > 85%
- [ ] 验证ETF成分股获取逻辑
- [ ] 测试赛道切换的平滑性

---

## 🔧 技术设计

### 1. 赛道配置文件

```yaml
# config/hot_sectors.yaml
version: "1.0.0"
enabled: false  # 初期关闭，稳定运行后手动切换
updated_at: "2025-12-01"

# 赛道定义
sectors:
  tech:
    name: "科技芯片"
    size: 20
    weight: 20%
    sources:
      - type: "etf"
        code: "000688"  # 科创50
        top_n: 10
      - type: "etf"
        code: "512760"  # 芯片ETF
        top_n: 10
    filters:
      min_avg_amount: 1000000000  # 10亿
      
  new_energy:
    name: "新能源 & 电动车"
    size: 20
    weight: 20%
    sources:
      - type: "etf"
        code: "159806"  # 新能源车ETF
        top_n: 12
      - type: "etf"
        code: "515790"  # 光伏ETF
        top_n: 8
        
  healthcare:
    name: "医药生物"
    size: 20
    weight: 20%
    sources:
      - type: "etf"
        code: "512290"  # 生物医药ETF
        top_n: 15
      - type: "manual"
        codes: ["300760", "688981", "603259", "002821", "300015"]
        
  consumer:
    name: "消费白酒"
    size: 15
    weight: 15%
    sources:
      - type: "etf"
        code: "512690"  # 白酒ETF
        top_n: 10
      - type: "manual"
        codes: ["600519", "000858", "000568", "002304", "603369"]
        
  finance:
    name: "金融周期"
    size: 15
    weight: 15%
    sources:
      - type: "etf"
        code: "512000"  # 券商ETF
        top_n: 5
      - type: "etf"
        code: "512800"  # 银行ETF
        top_n: 5
      - type: "etf"
        code: "512400"  # 有色金属ETF
        top_n: 5
        
  monster:
    name: "超级妖股"
    size: 10
    weight: 10%
    dynamic: true
    update_frequency: "weekly"
    criteria:
      - field: "涨幅_5日"
        operator: ">"
        value: 30
      - field: "换手率_5日"
        operator: ">"
        value: 10
      - field: "流通市值"
        operator: "<"
        value: 50000000000  # 500亿
```

### 2. 赛道股票池管理器

```python
# src/services/stock_pool/hot_sectors_manager.py
import akshare as ak
from typing import List, Dict
from pathlib import Path
import yaml

class HotSectorsManager:
    """热门赛道股票池管理器"""
    
    def __init__(self, config_path: str = "config/hot_sectors.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.cache_path = Path("cache/hot_sectors")
        self.cache_path.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    async def build_hot_sectors_pool(self) -> List[str]:
        """构建热门赛道股票池（100只）"""
        all_stocks = []
        
        for sector_id, sector_config in self.config["sectors"].items():
            if sector_config.get("dynamic", False):
                # 动态妖股池
                stocks = await self._get_monster_stocks(sector_config)
            else:
                # 静态赛道池
                stocks = await self._get_sector_stocks(sector_id, sector_config)
            
            all_stocks.extend(stocks)
            logger.info(f"赛道 {sector_config['name']}: {len(stocks)} 只股票")
        
        # 去重并限制数量
        unique_stocks = list(dict.fromkeys(all_stocks))[:100]
        
        # 保存到缓存
        await self._save_cache(unique_stocks)
        
        return unique_stocks
    
    async def _get_sector_stocks(self, sector_id: str, config: dict) -> List[str]:
        """获取赛道股票列表"""
        stocks = []
        
        for source in config["sources"]:
            if source["type"] == "etf":
                etf_stocks = await self._get_etf_stocks(
                    source["code"], 
                    source["top_n"]
                )
                stocks.extend(etf_stocks)
                
            elif source["type"] == "manual":
                stocks.extend(source["codes"])
        
        # 应用过滤器
        if "filters" in config:
            stocks = await self._apply_filters(stocks, config["filters"])
        
        # 限制数量
        return stocks[:config["size"]]
    
    async def _get_etf_stocks(self, etf_code: str, top_n: int) -> List[str]:
        """获取ETF成分股Top N"""
        try:
            # 方法1：尝试从akshare获取ETF持仓
            df = ak.fund_etf_fund_info_em(fund=etf_code)
            
            # 按持仓占比排序
            df_sorted = df.sort_values("持仓占比", ascending=False)
            return df_sorted.head(top_n)["股票代码"].tolist()
            
        except Exception as e:
            logger.warning(f"ETF {etf_code} 获取失败: {e}")
            
            # 方法2：降级方案 - 使用指数成分股
            try:
                df_index = ak.index_stock_cons(symbol=etf_code)
                return df_index.head(top_n)["品种代码"].tolist()
            except Exception as e2:
                logger.error(f"ETF {etf_code} 降级方案也失败: {e2}")
                return []
    
    async def _get_monster_stocks(self, config: dict) -> List[str]:
        """动态计算妖股池"""
        try:
            # 获取全市场A股列表
            df_all = ak.stock_zh_a_spot_em()
            
            # 应用筛选条件
            for criterion in config["criteria"]:
                field = criterion["field"]
                operator = criterion["operator"]
                value = criterion["value"]
                
                if operator == ">":
                    df_all = df_all[df_all[field] > value]
                elif operator == "<":
                    df_all = df_all[df_all[field] < value]
            
            # 按涨幅排序，取Top N
            df_sorted = df_all.sort_values("涨跌幅", ascending=False)
            return df_sorted.head(config["size"])["代码"].tolist()
            
        except Exception as e:
            logger.error(f"妖股池计算失败: {e}")
            return []
    
    async def _apply_filters(self, stocks: List[str], filters: dict) -> List[str]:
        """应用过滤条件（如最小成交额）"""
        if "min_avg_amount" not in filters:
            return stocks
        
        filtered = []
        for code in stocks:
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=(datetime.now() - timedelta(days=7)).strftime("%Y%m%d"),
                    end_date=datetime.now().strftime("%Y%m%d")
                )
                avg_amount = df["成交额"].mean()
                
                if avg_amount >= filters["min_avg_amount"]:
                    filtered.append(code)
            except:
                continue
        
        return filtered
    
    async def _save_cache(self, stocks: List[str]):
        """保存到缓存"""
        cache_file = self.cache_path / f"hot_sectors_{datetime.now().date()}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "stocks": stocks,
                "count": len(stocks)
            }, f, ensure_ascii=False, indent=2)
```

### 3. 池切换逻辑

```python
# src/services/stock_pool/pool_switcher.py
class StockPoolSwitcher:
    """股票池切换器"""
    
    def __init__(self):
        self.hs300_manager = StockPoolInitializer()
        self.hot_sectors_manager = HotSectorsManager()
        self.current_mode = "hs300"  # 默认使用沪深300
    
    async def get_current_pool(self) -> List[str]:
        """获取当前激活的股票池"""
        if self.current_mode == "hs300":
            return await self.hs300_manager.get_hs300_top100()
        elif self.current_mode == "hot_sectors":
            return await self.hot_sectors_manager.build_hot_sectors_pool()
        else:
            raise ValueError(f"Unknown pool mode: {self.current_mode}")
    
    async def switch_to_hot_sectors(self):
        """切换到热门赛道池"""
        logger.info("切换股票池: HS300 -> 热门赛道")
        self.current_mode = "hot_sectors"
        
        # 验证新股票池
        new_pool = await self.get_current_pool()
        if len(new_pool) < 50:
            logger.error(f"新股票池数量不足: {len(new_pool)}")
            self.current_mode = "hs300"  # 回滚
            raise ValueError("股票池切换失败")
        
        logger.info(f"股票池切换成功，新池大小: {len(new_pool)}")
    
    async def switch_to_hs300(self):
        """切换回沪深300池"""
        logger.info("切换股票池: 热门赛道 -> HS300")
        self.current_mode = "hs300"
```

---

## ✅ 测试计划

### 1. 单元测试

```python
# tests/test_hot_sectors_manager.py
@pytest.mark.asyncio
async def test_build_hot_sectors_pool():
    """测试热门赛道池构建"""
    manager = HotSectorsManager()
    pool = await manager.build_hot_sectors_pool()
    
    assert len(pool) == 100
    assert len(set(pool)) == 100  # 无重复

@pytest.mark.asyncio
async def test_monster_stocks_criteria():
    """测试妖股筛选条件"""
    manager = HotSectorsManager()
    monsters = await manager._get_monster_stocks({
        "size": 10,
        "criteria": [
            {"field": "涨跌幅", "operator": ">", "value": 5}
        ]
    })
    
    assert len(monsters) <= 10
```

### 2. 集成测试

```bash
# 验证ETF数据获取
docker compose -f docker-compose.dev.yml run --rm get-stockdata \
    python -m scripts.test_hot_sectors_build
```

---

## 📊 切换计划

1. **第1-2周**: 使用 HS300 Top 100（Story 004.01）
2. **第3周**: 准备热门赛道配置，验证数据获取
3. **第4周**: **手动切换**到热门赛道池（配置 `enabled: true`）
4. **第5周**: 观察数据质量和系统稳定性

---

## 📝 注意事项

1. **ETF数据源**: akshare的ETF接口可能不稳定，需双重降级方案
2. **妖股风险**: 动态妖股池可能包含低流动性股票，需严格过滤
3. **赛道权重**: 初期可手动调整各赛道占比，找到最优配置
4. **回滚机制**: 切换失败时自动回滚到HS300池

---

**创建时间**: 2025-12-01  
**创建人**: AI 系统架构师  
**审核人**: 待定
