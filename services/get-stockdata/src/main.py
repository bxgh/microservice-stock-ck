#!/usr/bin/env python3
"""
Get Stock Data Service - Pure API Layer

Architecture:
- API Routes (FastAPI)
- gRPC Client (communicates with mootdx-source)
- No direct data fetching logic
"""
import logging
import sys
import os
from contextlib import asynccontextmanager

# FORCE OVERRIDE for Docker Host Mode + Tunnel
# Since we cannot update container env vars easily without recreation
os.environ["GSD_DB_HOST"] = "127.0.0.1"
os.environ["GSD_DB_PORT"] = "36301"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Add user site-packages where asynch is installed
sys.path.append("/home/app/.local/lib/python3.12/site-packages")

# Import gRPC client
from grpc_client import get_datasource_client, close_datasource_client

# Import API routes
from api.quotes_routes import router as quotes_router
from api.finance_routes import router as finance_router
from api.valuation_routes import router as valuation_router
from api.market_routes import router as market_router
from api.liquidity_routes import router as liquidity_router
from api.stocks_routes import router as stocks_router
from api.health_routes import health_router
from api.sync_routes import router as sync_router
from api.quality_routes import router as quality_router
from api.repair_routes import router as repair_router

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("get-stockdata")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Get Stock Data Service...")
    
    try:
        # Initialize gRPC client
        client = await get_datasource_client()
        healthy = await client.health_check()
        
        if healthy:
            logger.info("✓ gRPC client connected to mootdx-source")
        else:
            logger.warning("⚠ mootdx-source health check failed")
            
    except Exception as e:
        logger.error(f"Failed to initialize gRPC client: {e}")
    
    logger.info("=== Get Stock Data Service Ready ===")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Get Stock Data Service...")
    await close_datasource_client()
    logger.info("✓ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Get Stock Data API",
    description="Stock data API layer - communicates with mootdx-source via gRPC",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(quotes_router)
app.include_router(finance_router)
app.include_router(valuation_router)
app.include_router(market_router)
app.include_router(liquidity_router)
app.include_router(stocks_router)
app.include_router(sync_router)
app.include_router(quality_router)
app.include_router(repair_router)

logger.info(f"Registered {len(app.routes)} routes")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "get-stockdata",
        "version": "2.0.0",
        "architecture": "Pure API Layer",
        "data_source": "mootdx-source (gRPC)",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8083")), # Using internal port
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="info"
    )
