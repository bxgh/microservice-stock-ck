# Implementation Plan - Story 5.6: Blacklist Pool

## Goal Description
Implement the **Blacklist Pool** to manage risk vetoes, preventing the system from trading high-risk stocks. This includes both permanent blacklists (e.g., ST, delisted) and temporary blacklists (e.g., technical stop-loss, fundamental warnings) with automated expiration logic.

## User Review Required
> [!IMPORTANT]
> **Expiration Logic**: We will implement a differentiated expiration mechanism:
> - **Technical Stop-loss**: 3 months cooling-off.
> - **Fundamental Risk**: 12 months cooling-off.
> - **Permanent**: No expiration.

## Proposed Changes

### Database Models
#### [NEW] [blacklist_models.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/database/blacklist_models.py)
- `BlacklistStock` table:
    - Fields: `reason_type` (tech_stop, fundamental, regulatory, permanent), `release_date`.
    - Index on `code` and `release_date` for fast queries.

### Service Layer
#### [NEW] [blacklist_service.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/services/stock_pool/blacklist_service.py)
- `add_to_blacklist(code, reason, type)`: Calculates `release_date` based on type.
- `is_blacklisted(code)`: Checks if code is in active blacklist.
- `clean_expired_blacklist()`: Scheduled task to remove expired entries.

### API
#### [NEW] [blacklist_routes.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/api/blacklist_routes.py)
- `POST /blacklist/check`: Batch check endpoint for risk control system.
- `GET /blacklist`: List all blocked stocks.
- `POST /blacklist`: Manual add (for admin/risk manager).

## Verification Plan

### Automated Tests
- **Integration Test**: `tests/test_blacklist_pool.py`
- **Scenarios**:
    - Add temporary blacklist -> Check expiration logic (mock time).
    - Add permanent blacklist -> Ensure never expires.
    - Batch check API returns correct status for mixed list.
