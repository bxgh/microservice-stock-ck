# Implementation Plan - Story 5.2: Candidate Pool

## Goal Description
Implement the **Candidate Pool** to bridge the gap between the broad Universe and the specific Position pool. This story focuses on the **Long-term Candidate Pool**, filtering the top 300 stocks from the Universe based on multi-factor scoring (Alpha 4D) and classifying them into specific strategy sub-pools (Dividend, Growth, Sector).

## User Review Required
> [!NOTE]
> **Unified Model**: We will use a single `CandidateStock` model for both Long-term (Story 5.2) and Swing (Story 5.3) candidates, distinguished by `pool_type`.

> [!IMPORTANT]
> **Scoring dependency**: The actual "Alpha 4D Scoring" logic comes from EPIC-002. For this infrastructure story, we will implement the *mechanism* to store scores and rank stocks, but the *calculation* will use a placeholder or basic mock until EPIC-002 is ready.

## Proposed Changes

### Database Models
#### [NEW] [candidate_models.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/database/candidate_models.py)
- `CandidateStock` table:
    - `pool_type`: 'long' or 'swing'
    - `sub_pool`: 'dividend', 'growth', 'sector'
    - `score`: Float score for ranking
    - `rank`: Integer rank within the pool

### Service Layer
#### [NEW] [candidate_service.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/services/stock_pool/candidate_service.py)
- `CandidatePoolService`:
    - `refresh_pool(pool_type)`: Main logic to pull from Universe, apply scoring (mock for now), and populate Candidate pool.
    - `classify_stock(stock)`: Logic to assign `sub_pool` (e.g., if `dividend_yield > 3%` -> Dividend).
    - `get_candidates(pool_type, sub_pool)`: Query method.

### API
#### [NEW] [candidate_routes.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/api/candidate_routes.py)
- `POST /candidates/refresh`: Trigger manual refresh.
- `GET /candidates/{pool_type}`: List candidates with filtering.

## Verification Plan

### Automated Tests
- **Integration Test**: `tests/test_candidate_pool.py`
- **Scenarios**:
    - **Classification**: Verify reasonable stocks are assigned to correct sub-pools (e.g., dummy stock with high growth -> Growth pool).
    - **Ranking**: Verify `rank` field respects the `score`.
    - **Persistence**: Verify pool is cleared and rebuilt on refresh.
