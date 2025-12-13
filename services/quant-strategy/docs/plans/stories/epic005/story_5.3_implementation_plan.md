# Implementation Plan - Story 5.3: Swing Candidate Pool

## Goal Description
Implement the **Swing Candidate Pool** focusing on short-term trading opportunities. This pool captures stocks with strong momentum, hot themes, or oversold conditions, utilizing the "Smart Money" flow analysis (mocked for now).

## User Review Required
> [!TIP]
> **Infrastructure Reuse**: We are reusing the `CandidateStock` model and API endpoints from Story 5.2. No DB schema changes required.

> [!IMPORTANT]
> **Scoring differentiation**:
> - **Long Pool**: Based on Fundamentals (Value/Growth).
> - **Swing Pool**: Based on **Money Flow** & **Technicals**.
> We will implement distinct logic branches in `CandidatePoolService`.

## Proposed Changes

### Service Layer
#### [MODIFY] [candidate_service.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/services/stock_pool/candidate_service.py)
- `_calculate_mock_score(stock, pool_type)`:
    - Add specific logic for `pool_type='swing'`.
    - Mock "Smart Money" inflow using random factors skewed by turnover rate and recent volatility.
- `_classify_stock(stock, pool_type)`:
    - Add logic for `swing` pool types:
        - **Momentum**: High recent rank.
        - **Theme**: Hot sector tag (Mock).
        - **Oversold**: Negative recent performance but high inflow (Mock).

### API
- **No changes required in routes**. `POST /candidates/refresh` and `GET /candidates/{pool_type}` already support parameterization.

## Verification Plan

### Automated Tests
- **Integration Test**: `tests/test_swing_pool.py`
- **Scenarios**:
    - **Isolation**: Verify refreshing 'swing' pool does NOT clear 'long' pool.
    - **Logic Check**: Verify Swing stocks have expected sub-pool tags (momentum, etc.).
    - **API Access**: Verify `/api/v1/candidates/swing` returns correct data.
