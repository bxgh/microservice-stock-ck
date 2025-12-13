"""
Universe Pool Service

Manages the Universe Pool (全市场基础池), including:
- Dynamic filter configuration
- Stock list retrieval from get-stockdata
- Qualification checking and filtering
- Persistence to Tencent Cloud MySQL
"""
import logging
import asyncio
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from database.stock_pool_models import UniverseStock, UniverseFilterConfig, PoolTransition
from adapters.stock_data_provider import data_provider

logger = logging.getLogger(__name__)


@dataclass
class RefreshResult:
    """刷新结果"""
    success: bool
    total_stocks: int
    qualified_count: int
    disqualified_count: int
    new_entries: int
    removed_entries: int
    duration_seconds: float
    message: str


@dataclass
class PoolStats:
    """池统计信息"""
    total_qualified: int
    total_disqualified: int
    by_exchange: Dict[str, int]
    avg_market_cap: float
    avg_turnover: float
    last_refresh: Optional[datetime]


class UniversePoolService:
    """
    Universe Pool 管理服务
    
    负责:
    1. 从 get-stockdata 获取全市场股票
    2. 根据动态配置进行筛选
    3. 持久化到腾讯云 MySQL
    4. 记录池流转历史
    """
    
    # 默认配置 (当数据库无配置时使用)
    DEFAULT_CONFIG = {
        'min_list_months': 12,
        'min_avg_turnover': 3000.0,
        'min_market_cap': 30.0,
        'min_turnover_ratio': 0.3
    }
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化服务"""
        if self._initialized:
            return
        
        await data_provider.initialize()
        
        # 确保默认配置存在
        await self._ensure_default_config()
        
        self._initialized = True
        logger.info("UniversePoolService initialized")
    
    async def _ensure_default_config(self) -> None:
        """确保默认配置存在于数据库"""
        async for session in get_session():
            result = await session.execute(
                select(UniverseFilterConfig).where(
                    UniverseFilterConfig.config_name == 'default'
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                default_config = UniverseFilterConfig(
                    config_name='default',
                    is_active=True,
                    description='Default Universe Pool filter configuration',
                    **self.DEFAULT_CONFIG
                )
                session.add(default_config)
                await session.commit()
                logger.info("Created default filter configuration")
    
    async def get_active_config(self) -> UniverseFilterConfig:
        """获取当前激活的筛选配置"""
        async for session in get_session():
            result = await session.execute(
                select(UniverseFilterConfig).where(
                    UniverseFilterConfig.is_active == True
                ).order_by(UniverseFilterConfig.updated_at.desc())
            )
            config = result.scalar_one_or_none()
            
            if not config:
                # 返回默认配置对象
                return UniverseFilterConfig(**self.DEFAULT_CONFIG, config_name='default', is_active=True)
            
            return config
    
    async def update_filter_config(
        self,
        min_list_months: Optional[int] = None,
        min_avg_turnover: Optional[float] = None,
        min_market_cap: Optional[float] = None,
        min_turnover_ratio: Optional[float] = None
    ) -> UniverseFilterConfig:
        """
        更新筛选配置
        
        Args:
            min_list_months: 最小上市月份
            min_avg_turnover: 最小日均成交额 (万元)
            min_market_cap: 最小市值 (亿元)
            min_turnover_ratio: 最小换手率 (%)
        
        Returns:
            更新后的配置
        """
        async for session in get_session():
            result = await session.execute(
                select(UniverseFilterConfig).where(
                    UniverseFilterConfig.config_name == 'default'
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                config = UniverseFilterConfig(config_name='default', is_active=True)
                session.add(config)
            
            # 更新非空字段
            if min_list_months is not None:
                config.min_list_months = min_list_months
            if min_avg_turnover is not None:
                config.min_avg_turnover = min_avg_turnover
            if min_market_cap is not None:
                config.min_market_cap = min_market_cap
            if min_turnover_ratio is not None:
                config.min_turnover_ratio = min_turnover_ratio
            
            config.updated_at = datetime.now()
            await session.commit()
            await session.refresh(config)
            
            logger.info(f"Filter config updated: {config}")
            return config
    
    async def refresh_universe_pool(
        self,
        triggered_by: str = "manual",
        job_id: Optional[str] = None
    ) -> RefreshResult:
        """
        刷新 Universe Pool
        
        由 task-scheduler 或手动触发调用。
        
        Args:
            triggered_by: 触发来源 ("manual", "task-scheduler")
            job_id: 调度任务ID (如有)
        
        Returns:
            刷新结果
        """
        start_time = datetime.now()
        logger.info(f"Starting Universe Pool refresh (triggered by: {triggered_by}, job_id: {job_id})")
        
        async with self._lock:
            try:
                # 1. 获取当前配置
                config = await self.get_active_config()
                logger.info(f"Using config: min_cap={config.min_market_cap}亿, min_turnover={config.min_avg_turnover}万")
                
                # 2. 从 get-stockdata 获取全市场股票
                all_stocks = await self._fetch_all_stocks()
                if not all_stocks:
                    return RefreshResult(
                        success=False,
                        total_stocks=0,
                        qualified_count=0,
                        disqualified_count=0,
                        new_entries=0,
                        removed_entries=0,
                        duration_seconds=(datetime.now() - start_time).total_seconds(),
                        message="Failed to fetch stock list from get-stockdata"
                    )
                
                logger.info(f"Fetched {len(all_stocks)} stocks from get-stockdata")
                
                # 3. 应用筛选规则
                qualified, disqualified = await self._apply_filters(all_stocks, config)
                
                # 4. 持久化到数据库
                new_entries, removed_entries = await self._persist_results(qualified, disqualified)
                
                duration = (datetime.now() - start_time).total_seconds()
                
                result = RefreshResult(
                    success=True,
                    total_stocks=len(all_stocks),
                    qualified_count=len(qualified),
                    disqualified_count=len(disqualified),
                    new_entries=new_entries,
                    removed_entries=removed_entries,
                    duration_seconds=duration,
                    message=f"Universe Pool refreshed: {len(qualified)} qualified stocks"
                )
                
                logger.info(f"✅ Universe Pool refresh complete: {result}")
                return result
                
            except Exception as e:
                logger.exception(f"Universe Pool refresh failed: {e}")
                return RefreshResult(
                    success=False,
                    total_stocks=0,
                    qualified_count=0,
                    disqualified_count=0,
                    new_entries=0,
                    removed_entries=0,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    message=f"Refresh failed: {str(e)}"
                )
    
    async def _fetch_all_stocks(self) -> List[Dict[str, Any]]:
        """从 get-stockdata 获取全市场股票列表"""
        try:
            stocks = await data_provider.get_all_stocks(limit=6000)
            return stocks
        except Exception as e:
            logger.error(f"Failed to fetch stock list: {e}")
            return []
    
    async def _apply_filters(
        self,
        stocks: List[Dict[str, Any]],
        config: UniverseFilterConfig
    ) -> tuple[List[Dict], List[Dict]]:
        """
        应用筛选规则
        
        Returns:
            (qualified_list, disqualified_list)
        """
        qualified = []
        disqualified = []
        
        today = date.today()
        min_list_date = today - relativedelta(months=config.min_list_months)
        
        for stock in stocks:
            code = stock.get('code', '')
            name = stock.get('name', '')
            
            # 准备筛选数据
            stock_data = {
                'code': code,
                'name': name,
                'list_date': stock.get('list_date'),
                'exchange': stock.get('exchange', self._get_exchange(code)),
                'avg_turnover_20d': stock.get('avg_turnover_20d', stock.get('turnover', 0)),
                'market_cap': stock.get('market_cap', stock.get('total_mv', 0)),
                'turnover_ratio_20d': stock.get('turnover_ratio_20d', stock.get('turnover_ratio', 0)),
            }
            
            # 应用筛选规则
            disqualify_reason = self._check_qualification(stock_data, config, min_list_date)
            
            if disqualify_reason:
                stock_data['is_qualified'] = False
                stock_data['disqualify_reason'] = disqualify_reason
                disqualified.append(stock_data)
            else:
                stock_data['is_qualified'] = True
                stock_data['disqualify_reason'] = None
                qualified.append(stock_data)
        
        logger.info(f"Filter results: {len(qualified)} qualified, {len(disqualified)} disqualified")
        return qualified, disqualified
    
    def _check_qualification(
        self,
        stock: Dict[str, Any],
        config: UniverseFilterConfig,
        min_list_date: date
    ) -> Optional[str]:
        """
        检查单只股票是否合格
        
        Returns:
            None 表示合格，否则返回不合格原因
        """
        code = stock.get('code', '')
        name = stock.get('name', '')
        
        # 规则1: ST/*ST 过滤
        if 'ST' in name.upper() or '*ST' in name.upper():
            return "ST股票"
        
        # 规则2: 上市时间检查
        list_date = stock.get('list_date')
        if list_date:
            if isinstance(list_date, str):
                try:
                    list_date = datetime.strptime(list_date, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        list_date = datetime.strptime(list_date, '%Y%m%d').date()
                    except ValueError:
                        list_date = None
            
            if list_date and list_date > min_list_date:
                return f"上市不足{config.min_list_months}个月"
        
        # 规则3: 成交额检查
        avg_turnover = stock.get('avg_turnover_20d', 0) or 0
        if avg_turnover < config.min_avg_turnover:
            return f"日均成交额{avg_turnover:.0f}万 < {config.min_avg_turnover}万"
        
        # 规则4: 市值检查
        market_cap = stock.get('market_cap', 0) or 0
        if market_cap < config.min_market_cap:
            return f"市值{market_cap:.1f}亿 < {config.min_market_cap}亿"
        
        # 规则5: 换手率检查
        turnover_ratio = stock.get('turnover_ratio_20d', 0) or 0
        if turnover_ratio < config.min_turnover_ratio:
            return f"换手率{turnover_ratio:.2f}% < {config.min_turnover_ratio}%"
        
        return None  # 合格
    
    def _get_exchange(self, code: str) -> str:
        """根据代码判断交易所"""
        if not code:
            return 'UNKNOWN'
        if code.startswith('6'):
            return 'SH'
        elif code.startswith(('0', '3')):
            return 'SZ'
        elif code.startswith(('4', '8')):
            return 'BJ'
        return 'UNKNOWN'
    
    async def _persist_results(
        self,
        qualified: List[Dict],
        disqualified: List[Dict]
    ) -> tuple[int, int]:
        """
        持久化筛选结果到数据库
        
        Returns:
            (new_entries_count, removed_entries_count)
        """
        async for session in get_session():
            # 获取当前数据库中的记录
            result = await session.execute(select(UniverseStock))
            existing_stocks = {s.code: s for s in result.scalars().all()}
            existing_qualified = {code for code, s in existing_stocks.items() if s.is_qualified}
            
            new_qualified_codes = {s['code'] for s in qualified}
            
            # 计算变更
            new_entries = new_qualified_codes - existing_qualified
            removed_entries = existing_qualified - new_qualified_codes
            
            # 更新或插入记录
            now = datetime.now()
            all_stocks = qualified + disqualified
            
            for stock_data in all_stocks:
                code = stock_data['code']
                existing = existing_stocks.get(code)
                
                if existing:
                    # 更新现有记录
                    existing.name = stock_data['name']
                    existing.exchange = stock_data.get('exchange')
                    existing.avg_turnover_20d = stock_data.get('avg_turnover_20d')
                    existing.market_cap = stock_data.get('market_cap')
                    existing.turnover_ratio_20d = stock_data.get('turnover_ratio_20d')
                    existing.is_qualified = stock_data['is_qualified']
                    existing.disqualify_reason = stock_data.get('disqualify_reason')
                    existing.updated_at = now
                else:
                    # 插入新记录
                    new_stock = UniverseStock(
                        code=code,
                        name=stock_data['name'],
                        list_date=stock_data.get('list_date') if isinstance(stock_data.get('list_date'), date) else None,
                        exchange=stock_data.get('exchange'),
                        avg_turnover_20d=stock_data.get('avg_turnover_20d'),
                        market_cap=stock_data.get('market_cap'),
                        turnover_ratio_20d=stock_data.get('turnover_ratio_20d'),
                        is_qualified=stock_data['is_qualified'],
                        disqualify_reason=stock_data.get('disqualify_reason'),
                        created_at=now,
                        updated_at=now
                    )
                    session.add(new_stock)
                
                # 记录流转 (新进入或移出)
                if code in new_entries:
                    transition = PoolTransition(
                        code=code,
                        from_pool=None,
                        to_pool='universe',
                        transition_date=now,
                        reason='Qualified based on filter criteria'
                    )
                    session.add(transition)
                elif code in removed_entries:
                    transition = PoolTransition(
                        code=code,
                        from_pool='universe',
                        to_pool=None,
                        transition_date=now,
                        reason=stock_data.get('disqualify_reason', 'No longer qualified')
                    )
                    session.add(transition)
            
            await session.commit()
            
            logger.info(f"Persisted {len(all_stocks)} stocks: {len(new_entries)} new, {len(removed_entries)} removed")
            return len(new_entries), len(removed_entries)
    
    async def get_qualified_stocks(
        self,
        limit: int = 5000,
        offset: int = 0
    ) -> List[UniverseStock]:
        """获取所有合格的股票"""
        async for session in get_session():
            result = await session.execute(
                select(UniverseStock)
                .where(UniverseStock.is_qualified == True)
                .offset(offset)
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_pool_stats(self) -> PoolStats:
        """获取池统计信息"""
        async for session in get_session():
            # 合格数量
            qualified_result = await session.execute(
                select(UniverseStock).where(UniverseStock.is_qualified == True)
            )
            qualified_stocks = qualified_result.scalars().all()
            
            # 不合格数量
            disqualified_result = await session.execute(
                select(UniverseStock).where(UniverseStock.is_qualified == False)
            )
            disqualified_stocks = disqualified_result.scalars().all()
            
            # 按交易所分组
            by_exchange = {}
            total_cap = 0.0
            total_turnover = 0.0
            
            for stock in qualified_stocks:
                exchange = stock.exchange or 'UNKNOWN'
                by_exchange[exchange] = by_exchange.get(exchange, 0) + 1
                total_cap += stock.market_cap or 0
                total_turnover += stock.avg_turnover_20d or 0
            
            qualified_count = len(qualified_stocks)
            
            # 最后刷新时间
            last_refresh = None
            if qualified_stocks:
                last_refresh = max(s.updated_at for s in qualified_stocks)
            
            return PoolStats(
                total_qualified=qualified_count,
                total_disqualified=len(disqualified_stocks),
                by_exchange=by_exchange,
                avg_market_cap=total_cap / qualified_count if qualified_count > 0 else 0,
                avg_turnover=total_turnover / qualified_count if qualified_count > 0 else 0,
                last_refresh=last_refresh
            )


# 全局单例
universe_pool_service = UniversePoolService()
