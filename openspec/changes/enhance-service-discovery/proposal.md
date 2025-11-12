# Change: Enhance TaskScheduler Service Discovery and Deployment

## Why

TaskScheduler has basic Nacos integration but lacks robust service discovery, automated deployment, and comprehensive monitoring capabilities needed for production microservice environments.

## What Changes

- **ADDED**: Enhanced service discovery with automatic re-registration and health monitoring
- **ADDED**: Unified deployment automation with multi-environment support
- **ADDED**: Comprehensive monitoring and metrics collection
- **ADDED**: Hot-reload configuration management
- **MODIFIED**: Consolidate multiple entry points into single configurable application

## Impact

- Affected specs: service-discovery, deployment-automation, monitoring-enhancement
- Affected code: `src/app.py`, `src/main*.py`, `registry/`, deployment scripts
- **Breaking Changes**: Low - mainly additive improvements
- Migration Effort: Minimal - existing functionality preserved