"""
Prometheus Metrics Endpoint

Exposes application metrics in Prometheus format for monitoring and alerting.
Includes metrics for:
- Request count and latency
- Stock pool size
- Promotion monitor stats
- Circuit breaker states
- Data source health
"""
import logging
from typing import Optional
from fastapi import APIRouter, Response, Request
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    generate_latest, CONTENT_TYPE_LATEST,
    REGISTRY, CollectorRegistry
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Monitoring"])

# ============ Request Metrics ============

REQUEST_COUNT = Counter(
    'stockdata_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'stockdata_request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# ============ Stock Pool Metrics ============

POOL_SIZE = Gauge(
    'stockdata_pool_size',
    'Current stock pool size',
    ['pool_type']  # core, promoted, manual, total
)

PROMOTED_STOCKS = Gauge(
    'stockdata_promoted_stocks',
    'Number of stocks currently in promotion pool'
)

MANUAL_STOCKS = Gauge(
    'stockdata_manual_stocks',
    'Number of manually added stocks'
)

# ============ Promotion Monitor Metrics ============

PROMOTION_SCANS = Counter(
    'stockdata_promotion_scans_total',
    'Total number of surge rank scans performed'
)

PROMOTION_EVENTS = Counter(
    'stockdata_promotion_events_total',
    'Total number of stocks promoted'
)

PROMOTION_MONITOR_RUNNING = Gauge(
    'stockdata_promotion_monitor_running',
    'Whether promotion monitor is running (1=yes, 0=no)'
)

# ============ Data Source Metrics ============

DATA_SOURCE_REQUESTS = Counter(
    'stockdata_source_requests_total',
    'Total requests to data sources',
    ['source', 'status']
)

DATA_SOURCE_LATENCY = Histogram(
    'stockdata_source_latency_seconds',
    'Data source request latency',
    ['source'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

CIRCUIT_BREAKER_STATE = Gauge(
    'stockdata_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['source']
)

# ============ Collection Metrics ============

COLLECTION_ROUNDS = Counter(
    'stockdata_collection_rounds_total',
    'Total data collection rounds executed'
)

COLLECTION_STOCKS = Gauge(
    'stockdata_collection_stocks',
    'Number of stocks in last collection round'
)

COLLECTION_SUCCESS_RATE = Gauge(
    'stockdata_collection_success_rate',
    'Success rate of last collection round (0-1)'
)

# ============ System Info ============

SERVICE_INFO = Info(
    'stockdata_service',
    'Service information'
)

# Set service info once
SERVICE_INFO.info({
    'name': 'get-stockdata',
    'version': '1.0.0',
    'environment': 'development'
})


@router.get("/metrics")
async def prometheus_metrics(request: Request):
    """
    Prometheus metrics endpoint
    
    Returns metrics in Prometheus text format for scraping.
    """
    try:
        # Update dynamic metrics before generating output
        await _update_dynamic_metrics(request)
        
        # Generate Prometheus format output
        metrics_output = generate_latest(REGISTRY)
        
        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {e}\n",
            media_type="text/plain",
            status_code=500
        )


async def _update_dynamic_metrics(request: Request):
    """Update metrics that need to be refreshed on each scrape"""
    try:
        app = request.app
        
        # Update stock pool metrics
        if hasattr(app.state, 'dynamic_manager'):
            dm = app.state.dynamic_manager
            stats = await dm.get_stats()
            
            POOL_SIZE.labels(pool_type='promoted').set(stats.get('promoted_count', 0))
            POOL_SIZE.labels(pool_type='manual').set(stats.get('manual_count', 0))
            POOL_SIZE.labels(pool_type='dynamic_total').set(stats.get('total_dynamic', 0))
            
            PROMOTED_STOCKS.set(stats.get('promoted_count', 0))
            MANUAL_STOCKS.set(stats.get('manual_count', 0))
        
        # Update promotion monitor metrics
        if hasattr(app.state, 'promotion_monitor'):
            pm = app.state.promotion_monitor
            pm_stats = pm.get_stats()
            
            PROMOTION_MONITOR_RUNNING.set(1 if pm_stats.get('running', False) else 0)
            
    except Exception as e:
        logger.warning(f"Error updating dynamic metrics: {e}")


# ============ Helper Functions for Recording Metrics ============

def record_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record a request metric"""
    status = "success" if status_code < 400 else "client_error" if status_code < 500 else "server_error"
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_data_source_request(source: str, success: bool, duration: float):
    """Record a data source request metric"""
    status = "success" if success else "error"
    DATA_SOURCE_REQUESTS.labels(source=source, status=status).inc()
    DATA_SOURCE_LATENCY.labels(source=source).observe(duration)


def record_promotion_scan(stocks_promoted: int):
    """Record a promotion scan event"""
    PROMOTION_SCANS.inc()
    PROMOTION_EVENTS.inc(stocks_promoted)


def record_collection_round(stocks_count: int, success_rate: float):
    """Record a collection round"""
    COLLECTION_ROUNDS.inc()
    COLLECTION_STOCKS.set(stocks_count)
    COLLECTION_SUCCESS_RATE.set(success_rate)


def update_circuit_breaker(source: str, state: str):
    """Update circuit breaker state metric"""
    state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state.lower(), -1)
    CIRCUIT_BREAKER_STATE.labels(source=source).set(state_value)
