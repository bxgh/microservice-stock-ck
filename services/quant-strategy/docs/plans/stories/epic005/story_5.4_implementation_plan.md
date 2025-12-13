# Story 5.4 Implementation Plan - Position Pool

## Goal
Implement the **Position Pool** (持仓池) to manage actual holdings, track profit/loss, enforce stop-loss/take-profit rules, and provide liquidity risk management.

## Requirements Reference
- **Epic**: EPIC-005 Stock Pool Management
- **Story**: 5.4 Position Pool
- **Priority**: P0

## Proposed Changes

### 1. Database Schema (`src/database/position_models.py`) [NEW]
Create `PositionStock` model with fields:
- Basic: `code`, `name`, `strategy_type` (long_term/swing)
- Trading: `entry_price`, `quantity`, `entry_date`, `current_price`
- P&L: `profit_loss`, `profit_loss_pct`
- Risk: `stop_loss`, `take_profit`, `holding_days`
- **Liquidity**:
    - `position_value`: Float (Market Value)
    - `avg_daily_volume`: Float (20d avg)
    - `liquidity_impact`: Enum (LOW/MEDIUM/HIGH)
    - `liquidation_cost_est`: Float (Estimated impact cost)

### 2. Service Layer (`src/services/stock_pool/position_pool_service.py`) [NEW]
Implement `PositionPoolService`:
- `add_position(code, quantity, price, strategy_type)`: Entry logic
- `check_liquidity_impact(code, quantity, price)`: **Pre-trade check**
    - Warn if `position_value > 0.1 * avg_daily_volume`
- `update_market_data()`: Sync capability (fetch latest price from `get-stockdata`)
- `calculate_pnl()`: Update P&L stats
- `get_positions()`: List current holdings

### 3. API Layer (`src/api/position_pool_routes.py`) [NEW]
Endpoints:
- `GET /api/v1/pools/position`: List all positions
- `POST /api/v1/pools/position`: Manually add position (simulation mode)
- `POST /api/v1/pools/position/liquidity-check`: Pre-trade check endpoint
- `GET /api/v1/pools/position/stats`: Portfolio summary

### 4. Integration
- Register models in `src/database/__init__.py`
- Register routes in `src/main.py`

## Verification Plan

### Automated Tests
1. **Liquidity Check Test**:
    - Mock stock with low volume.
    - Verify `check_liquidity_impact` returns HIGH impact warning for large quantity.
2. **P&L Calculation Test**:
    - Verify accumulation of profit/loss.
3. **Database Persistence**:
    - Verify CRUD operations.

### Manual Verification
- Use Swagger UI to add a position and check calculated fields.
- Trigger liquidity warning via API.
