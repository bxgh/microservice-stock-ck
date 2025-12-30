# Domain Architecture: Strategy & Batch Processing

## 1. Introduction
This document details the architecture for the Strategy and Batch Processing sub-domain of the `get-stockdata` service. It focuses on the high-level orchestration of data acquisition tasks, ensuring reliability and efficiency.

## 2. Component Architecture

### 2.1 100% Success Strategy Engine (GuaranteedSuccessStrategy)

```mermaid
graph TB
    subgraph "GuaranteedSuccessStrategy"
        subgraph "智能搜索矩阵"
            SM[搜索矩阵管理器]
            VP[验证引擎]
            QM[质量监控]
        end

        subgraph "多源切换策略"
            PPM[优先级管理器]
            FOM[故障转移管理器]
            HCM[健康检查管理器]
        end

        subgraph "执行引擎"
            TPE[线程池执行器]
            CM[并发管理器]
            RM[结果管理器]
        end
    end

    SM --> VP
    VP --> QM
    PPM --> FOM
    FOM --> HCM
    TPE --> CM
    CM --> RM
```

**Core Features:**
- Search Matrix based on verified success areas (e.g., Vanke A verification area)
- Intelligent multi-source switching and failover
- Strict data validation and quality assurance
- High concurrency execution and result aggregation

### 2.2 Batch Task Scheduler (BatchTaskScheduler)

```mermaid
graph TB
    subgraph "BatchTaskScheduler"
        subgraph "队列管理"
            UQ[紧急队列]
            HQ[高优先级队列]
            NQ[普通队列]
            LQ[低优先级队列]
        end

        subgraph "并发控制"
            TC[任务控制器]
            CC[并发管理器]
            SC[调度控制器]
        end

        subgraph "监控统计"
            ES[执行统计]
            PM[性能监控]
            RM[资源监控]
        end
    end

    UQ --> TC
    HQ --> TC
    NQ --> TC
    LQ --> TC
    TC --> CC
    CC --> SC
    SC --> ES
    ES --> PM
    PM --> RM
```

**Scheduling Strategy:**
- Four-level priority queue management (Urgent, High, Normal, Low)
- Intelligent concurrency control and resource management
- Real-time execution statistics and performance monitoring
- Dynamic load balancing and task reassignment

## 3. API Interface

### 3.1 100% Success Strategy API

**Endpoints:**
- `POST /api/v1/strategy/execute` - Execute guaranteed success strategy
- `GET /api/v1/strategy/status` - Get strategy status
- `POST /api/v1/strategy/config` - Strategy configuration management

### 3.2 Batch Processing API

**Endpoints:**
- `POST /api/v1/batch/submit` - Submit batch task
- `GET /api/v1/batch/status/{task_id}` - Query task status
- `GET /api/v1/batch/result/{task_id}` - Get task result
