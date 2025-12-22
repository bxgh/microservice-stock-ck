# Example Service Initialization for main.py
# Add this to your startup event handler

@app.on_event("startup")
async def startup_event():
    \"\"\"Initialize all services with proper dependency injection\"\"\"
    
    # 1. Initialize data provider
    from adapters.stock_data_provider import data_provider
    await data_provider.initialize()
    logger.info("Data provider initialized")
    
    # 2. Initialize scoring services
    from services.alpha.fundamental_scoring_service import FundamentalScoringService
    from services.alpha.valuation_service import ValuationService
    
    fundamental_scoring = FundamentalScoringService(
        data_provider=data_provider
    )
    await fundamental_scoring.initialize()
    logger.info("Fundamental scoring service initialized")
    
    valuation_service = ValuationService(
        data_provider=data_provider
    )
    await valuation_service.initialize()
    logger.info("Valuation service initialized")
    
    # 3. Initialize candidate pool service with scoring services
    from services.stock_pool.candidate_service import CandidatePoolService
    
    candidate_service = CandidatePoolService(
        data_provider=data_provider,
        fundamental_scoring=fundamental_scoring,
        valuation_service=valuation_service
    )
    logger.info("Candidate pool service initialized with real Alpha scoring")
    
    # Store in app state for route access
    app.state.data_provider = data_provider
    app.state.fundamental_scoring = fundamental_scoring
    app.state.valuation_service = valuation_service
    app.state.candidate_service = candidate_service
    
    logger.info("✅ All services initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    \"\"\"Clean up resources\"\"\"
    
    if hasattr(app.state, 'data_provider'):
        await app.state.data_provider.close()
    
    if hasattr(app.state, 'fundamental_scoring'):
        await app.state.fundamental_scoring.close()
    
    if hasattr(app.state, 'valuation_service'):
        await app.state.valuation_service.close()
    
    logger.info("All services closed")
