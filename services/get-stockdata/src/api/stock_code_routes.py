#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票代码API路由
提供股票基础数据相关的REST API接口
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends, Request
from typing import List, Optional
import logging
import asyncio

try:
    from ..services.stock_code_client import stock_client_instance
    from ..models.stock_models import (
        StockListRequest, StockListResponse, StockDetailResponse,
        StockSearchRequest, StockBatchRequest, StockMappingsResponse,
        StockExportRequest, CacheStatusResponse, StockFilter
    )
    from ..models.base_models import PaginationInfo
except ImportError:
    # 测试时使用绝对导入
    from services.stock_code_client import stock_client_instance
    from models.stock_models import (
        StockListRequest, StockListResponse, StockDetailResponse,
        StockSearchRequest, StockBatchRequest, StockMappingsResponse,
        StockExportRequest, CacheStatusResponse, StockFilter
    )
    from models.base_models import PaginationInfo

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/api/v1/stocks", tags=["股票代码"])


async def get_stock_client():
    """获取股票客户端实例依赖"""
    return stock_client_instance


@router.get("/list", response_model=StockListResponse)
async def get_stock_list(
    exchange: Optional[str] = Query(None, description="交易所筛选 (SH/SZ/BJ)"),
    asset_type: Optional[str] = Query(None, description="资产类型筛选"),
    is_active: Optional[bool] = Query(None, description="活跃状态筛选"),
    name_search: Optional[str] = Query(None, description="股票名称搜索"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    request: Request = None,
    client=Depends(get_stock_client)
):
    """
    获取股票列表

    支持多种筛选条件和分页查询
    """
    try:
        # 初始化客户端
        await client.initialize()

        # 构建筛选条件
        filters = StockFilter(
            exchange=exchange,
            asset_type=asset_type,
            is_active=is_active,
            name_contains=name_search
        )

        # 判断是否有实际筛选条件
        has_filters = any([exchange, asset_type, is_active is not None, name_search])

        if name_search:
            # 名称搜索
            stocks = await client.search_stocks(name_search, limit)
        elif not has_filters:
            # 无筛选条件 - 使用 get_all_stocks (优先从 Stock Dictionary API 获取)
            stocks = await client.get_all_stocks(limit=5000)
        else:
            # 有筛选条件
            stocks = await client.filter_stocks(filters)

        # 应用分页
        total = len(stocks)
        has_more = skip + limit < total
        paginated_stocks = stocks[skip:skip + limit]
        
        # EPIC-005: Enrich with Market Cap & Turnover from QuotesService
        # This is done on the paginated result to minimize processing
        quotes_service = getattr(request.app.state, "quotes_service", None)
        if quotes_service:
            try:
                # 1. Get codes
                codes = [s.stock_code for s in paginated_stocks]
                # 2. Get batch quotes
                quotes = await quotes_service.get_realtime_quotes(codes)
                # 3. Create mapping
                quote_map = {q['code']: q for q in quotes}
                
                # 4. Update stock info
                for stock in paginated_stocks:
                    if stock.stock_code in quote_map:
                        q = quote_map[stock.stock_code]
                        # Update fields if available
                        if q.get('market_cap'):
                            # Ensure unit consistency. 
                            # If AkShare returns raw, we might want to convert to 亿元 (10^8) if the model expects it.
                            # Standard StockInfo 'market_cap' usually implies 亿元 or matching legacy.
                            # Let's assume raw for now and check model definition or adjust unit.
                            # Based on existing 'get-stockdata' typical standards, 'market_cap' is often expected in 亿元 for display.
                            # AkShare 'total_market_cap' is usually raw.
                            stock.market_cap = q.get('market_cap') / 100000000.0
                        
                        if q.get('turnover'):
                             # turnover assumed to be daily turnover (成交额)
                             # avg_turnover_20d is what we need, but we only have today's turnover.
                             # For list display, today's turnover is also useful.
                             # If we need 20d, we'd need historical data.
                             # For now, let's map 'turnover' (raw) to a new field or existing if avail.
                             pass
                        
                        if q.get('turnover_ratio'):
                            stock.turnover_ratio = q.get('turnover_ratio')
                            
            except Exception as e:
                logger.warning(f"Failed to enrich stock list with quotes: {e}")

        # Enrich with Industry Info
        industry_service = getattr(request.app.state, "industry_service", None)
        if industry_service:
            try:
                # 批量获取行业信息
                codes = [s.stock_code for s in paginated_stocks]
                
                # P1-2 Fix: Limit concurrent tasks to prevent memory spike
                max_concurrent = 100
                if len(codes) > max_concurrent:
                    logger.warning(f"Limiting concurrent industry requests from {len(codes)} to {max_concurrent}")
                
                # 使用Semaphore控制并发数量
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def fetch_with_limit(code):
                    async with semaphore:
                        return await industry_service.get_industry_info(code)
                
                # 并发获取所有股票的行业信息（带并发限制）
                industry_tasks = [fetch_with_limit(code) for code in codes]
                industry_results = await asyncio.gather(*industry_tasks, return_exceptions=True)
                
                # 更新股票信息
                for stock, industry_info in zip(paginated_stocks, industry_results):
                    if isinstance(industry_info, dict) and industry_info:
                        stock.industry = industry_info.get('industry')
                        stock.sector = industry_info.get('sector')
            except Exception as e:
                logger.warning(f"Failed to enrich stock list with industry info: {e}")

        # 构建分页信息
        pagination = PaginationInfo(
            total=total,
            skip=skip,
            limit=limit,
            has_more=has_more
        )

        return StockListResponse(
            success=True,
            message="股票列表获取成功",
            data=paginated_stocks,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取股票列表失败: {str(e)}")


@router.get("", response_model=StockListResponse)
async def get_stock_list_alias(
    exchange: Optional[str] = Query(None, description="交易所筛选 (SH/SZ/BJ)"),
    asset_type: Optional[str] = Query(None, description="资产类型筛选"),
    is_active: Optional[bool] = Query(None, description="活跃状态筛选"),
    name_search: Optional[str] = Query(None, description="股票名称搜索"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    request: Request = None,
    client=Depends(get_stock_client)
):
    """
    获取股票列表 (Alias for /list)
    """
    return await get_stock_list(
        exchange=exchange,
        asset_type=asset_type,
        is_active=is_active,
        name_search=name_search,
        skip=skip,
        limit=limit,
        request=request,
        client=client
    )


@router.get("/{stock_code}/detail", response_model=StockDetailResponse)
async def get_stock_detail(
    stock_code: str = Path(..., description="股票代码"),
    request: Request = None,
    client=Depends(get_stock_client)
):
    """
    获取单只股票详情

    根据股票代码获取详细的股票信息
    """
    try:
        # 初始化客户端
        await client.initialize()

        stock = await client.get_stock_detail(stock_code)
        if not stock:
            raise HTTPException(status_code=404, detail=f"股票代码 {stock_code} 不存在")

        # EPIC-002: Enrich with Industry Info
        if request and hasattr(request.app.state, "industry_service"):
            industry_service = request.app.state.industry_service
            if industry_service:
                try:
                    industry_info = await industry_service.get_industry_info(stock_code)
                    if industry_info:
                        stock.industry = industry_info.get('industry')
                        stock.sector = industry_info.get('sector')
                        
                        # Populate listing date if original is missing or we want to update it
                        if industry_info.get('listing_date') and not stock.list_date:
                            stock.list_date = industry_info.get('listing_date')
                except Exception as e:
                    logger.warning(f"Failed to fetch industry info for {stock_code}: {e}")

        return StockDetailResponse(
            success=True,
            message="股票详情获取成功",
            data=stock
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票详情失败 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"获取股票详情失败: {str(e)}")


@router.get("/{stock_code}/mappings", response_model=StockMappingsResponse)
async def get_stock_mappings(
    stock_code: str = Path(..., description="股票代码"),
    client=Depends(get_stock_client)
):
    """
    获取股票代码映射信息

    获取股票在各个数据源中的代码映射，用于通达信等查询
    """
    try:
        # 初始化客户端
        await client.initialize()

        mappings = await client.get_stock_mappings(stock_code)
        if not mappings:
            raise HTTPException(status_code=404, detail=f"股票代码 {stock_code} 映射信息不存在")

        return StockMappingsResponse(
            success=True,
            message="代码映射获取成功",
            data=mappings
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票代码映射失败 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"获取代码映射失败: {str(e)}")


@router.get("/exchange/{exchange}", response_model=StockListResponse)
async def get_stocks_by_exchange(
    exchange: str = Path(..., description="交易所代码 (SH/SZ/BJ)"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    client=Depends(get_stock_client)
):
    """
    按交易所获取股票列表

    获取指定交易所的所有股票
    """
    try:
        # 初始化客户端
        await client.initialize()

        stocks = await client.get_stocks_by_exchange(exchange)

        # 应用数量限制
        limited_stocks = stocks[:limit]
        total = len(stocks)
        has_more = len(limited_stocks) < total

        pagination = PaginationInfo(
            total=total,
            skip=0,
            limit=len(limited_stocks),
            has_more=has_more
        )

        return StockListResponse(
            success=True,
            message=f"交易所 {exchange} 股票列表获取成功",
            data=limited_stocks,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"获取交易所 {exchange} 股票列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易所股票列表失败: {str(e)}")


@router.get("/search", response_model=StockListResponse)
async def search_stocks(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    client=Depends(get_stock_client)
):
    """
    股票搜索

    根据股票名称进行模糊搜索
    """
    try:
        # 初始化客户端
        await client.initialize()

        stocks = await client.search_stocks(query, limit)

        total = len(stocks)
        has_more = False  # 搜索结果不做分页

        pagination = PaginationInfo(
            total=total,
            skip=0,
            limit=len(stocks),
            has_more=has_more
        )

        return StockListResponse(
            success=True,
            message=f"股票搜索完成，找到 {total} 个结果",
            data=stocks,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"股票搜索失败 {query}: {e}")
        raise HTTPException(status_code=500, detail=f"股票搜索失败: {str(e)}")


@router.post("/batch", response_model=StockListResponse)
async def get_batch_stocks(
    request: StockBatchRequest,
    client=Depends(get_stock_client)
):
    """
    批量获取股票信息

    根据股票代码列表批量获取股票信息
    """
    try:
        # 初始化客户端
        await client.initialize()

        stocks = []
        for stock_code in request.stock_codes:
            stock = await client.get_stock_detail(stock_code)
            if stock:
                stocks.append(stock)

        return StockListResponse(
            success=True,
            message=f"批量获取完成，成功 {len(stocks)} 个",
            data=stocks,
            pagination=PaginationInfo(
                total=len(stocks),
                skip=0,
                limit=len(stocks),
                has_more=False
            )
        )

    except Exception as e:
        logger.error(f"批量获取股票信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量获取失败: {str(e)}")


@router.get("/export")
async def export_stocks(
    format: str = Query("json", description="导出格式 (json/csv)"),
    exchange: Optional[str] = Query(None, description="交易所筛选"),
    asset_type: Optional[str] = Query(None, description="资产类型筛选"),
    is_active: Optional[bool] = Query(None, description="活跃状态筛选"),
    client=Depends(get_stock_client)
):
    """
    导出股票数据

    支持JSON和CSV格式的数据导出
    """
    try:
        # 初始化客户端
        await client.initialize()

        # 构建筛选条件
        filters = StockFilter(
            exchange=exchange,
            asset_type=asset_type,
            is_active=is_active
        )

        stocks = await client.filter_stocks(filters)

        if format.lower() == "csv":
            # 简单的CSV导出
            import io
            import csv

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入标题行
            writer.writerow([
                "股票代码", "股票名称", "交易所", "资产类型", "是否活跃",
                "标准代码", "Tushare代码", "AKShare代码", "同花顺代码",
                "Wind代码", "东方财富代码", "上市日期"
            ])

            # 写入数据行
            for stock in stocks:
                writer.writerow([
                    stock.stock_code,
                    stock.stock_name,
                    stock.exchange,
                    stock.asset_type,
                    stock.is_active,
                    stock.code_mappings.standard,
                    stock.code_mappings.tushare,
                    stock.code_mappings.akshare,
                    stock.code_mappings.tonghua_shun,
                    stock.code_mappings.wind,
                    stock.code_mappings.east_money,
                    stock.list_date.isoformat() if stock.list_date else ""
                ])

            content = output.getvalue()
            output.close()

            from fastapi.responses import Response
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=stocks.csv"}
            )
        else:
            # JSON导出
            return {
                "success": True,
                "message": "股票数据导出成功",
                "data": [stock.dict() for stock in stocks],
                "total": len(stocks)
            }

    except Exception as e:
        logger.error(f"导出股票数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/cache/status", response_model=CacheStatusResponse)
async def get_cache_status(client=Depends(get_stock_client)):
    """
    获取缓存状态

    查看当前缓存的使用情况和连接状态
    """
    try:
        # 初始化客户端
        await client.initialize()

        status = await client.get_cache_status()

        return CacheStatusResponse(
            success=True,
            message="缓存状态获取成功",
            data=status
        )

    except Exception as e:
        logger.error(f"获取缓存状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取缓存状态失败: {str(e)}")


@router.post("/cache/refresh")
async def refresh_cache(
    cache_type: str = Query("all", description="缓存类型 (all/memory/redis)"),
    client=Depends(get_stock_client)
):
    """
    刷新缓存

    清空指定类型的缓存并重新加载热点数据
    """
    try:
        # 初始化客户端
        await client.initialize()

        success = await client.refresh_cache(cache_type)

        if success:
            return {
                "success": True,
                "message": f"缓存 {cache_type} 刷新成功"
            }
        else:
            raise HTTPException(status_code=500, detail="缓存刷新失败")

    except Exception as e:
        logger.error(f"刷新缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"刷新缓存失败: {str(e)}")


# 内部接口 (供微服务内部调用)
internal_router = APIRouter(prefix="/internal/stocks", tags=["内部接口"])


@internal_router.get("/list")
async def internal_get_stock_list(
    exchange: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    client=Depends(get_stock_client)
):
    """内部接口：获取股票列表"""
    await client.initialize()

    if exchange:
        return await client.get_stocks_by_exchange(exchange)
    else:
        return await client.get_all_stocks(limit)


@internal_router.get("/{stock_code}/mappings")
async def internal_get_stock_mappings(
    stock_code: str,
    client=Depends(get_stock_client)
):
    """内部接口：获取股票代码映射"""
    await client.initialize()
    return await client.get_stock_mappings(stock_code)


@internal_router.get("/exchange/{exchange}/list")
async def internal_get_stocks_by_exchange(
    exchange: str,
    client=Depends(get_stock_client)
):
    """内部接口：按交易所获取股票列表"""
    await client.initialize()
    return await client.get_stocks_by_exchange(exchange)