from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from src.core.stock_pool.service import StockPoolService

router = APIRouter(prefix="/api/v1/pools", tags=["Stock Pool Management"])

# Schemas
class StockItemBase(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    weight: float = 1.0

class StockItemCreate(StockItemBase):
    pass

class StockItemResponse(StockItemBase):
    id: int
    pool_id: int
    
    class Config:
        from_attributes = True

class PoolBase(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: str = "manual"

class PoolCreate(PoolBase):
    pass

class PoolResponse(PoolBase):
    id: int
    items: List[StockItemResponse] = []
    
    class Config:
        from_attributes = True

# Dependency
async def get_service():
    return StockPoolService()

# Routes
@router.post("/", response_model=PoolResponse, status_code=status.HTTP_201_CREATED)
async def create_pool(pool: PoolCreate, service: StockPoolService = Depends(get_service)):
    try:
        return await service.create_pool(pool.name, pool.description, pool.strategy_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[PoolResponse])
async def list_pools(service: StockPoolService = Depends(get_service)):
    return await service.get_pools()

@router.get("/{pool_id}", response_model=PoolResponse)
async def get_pool(pool_id: int, service: StockPoolService = Depends(get_service)):
    pool = await service.get_pool_by_id(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    return pool

@router.delete("/{pool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pool(pool_id: int, service: StockPoolService = Depends(get_service)):
    success = await service.delete_pool(pool_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pool not found")

@router.post("/{pool_id}/stocks", response_model=StockItemResponse)
async def add_stock_to_pool(
    pool_id: int, 
    item: StockItemCreate, 
    service: StockPoolService = Depends(get_service)
):
    try:
        return await service.add_stock(pool_id, item.stock_code, item.stock_name, item.weight)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{pool_id}/stocks/{stock_code}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_stock_from_pool(
    pool_id: int, 
    stock_code: str, 
    service: StockPoolService = Depends(get_service)
):
    success = await service.remove_stock(pool_id, stock_code)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
