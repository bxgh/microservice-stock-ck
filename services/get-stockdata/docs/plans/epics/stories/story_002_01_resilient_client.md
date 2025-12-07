# Story 002-01: 智能重试与熔断机制

**Story ID**: STORY-002-01  
**Epic**: EPIC-002 高可用采集引擎  
**优先级**: P0  
**估算**: 3 天  
**状态**: 进行中

---

## 📋 Story 概述

为数据采集引擎增加智能重试和熔断机制，确保在网络不稳定或服务端繁忙时，系统能够自动重试并在持续失败时进行自我保护。

### 业务价值
- 采集成功率从 ~95% 提升到 >99.8%
- 减少人工干预频率（从每天多次降至每周≤1次）
- 系统具备自我修复能力

---

## 🎯 验收标准

### 功能验收
- [ ] 实现指数退避重试算法（1s, 2s, 4s, 8s, 16s）
- [ ] 网络错误时自动重试，最多 5 次
- [ ] 连续失败 5 次触发熔断（Circuit Breaker OPEN）
- [ ] 熔断后 10 分钟自动尝试恢复（HALF_OPEN）
- [ ] 恢复成功后关闭熔断器（CLOSED）

### 性能验收
- [ ] 重试成功率 > 80%（统计验证）
- [ ] 重试不影响正常请求延迟（< 10ms 额外开销）
- [ ] 单次重试的最大延迟 < 32 秒（1+2+4+8+16）

### 测试验收
- [ ] 单元测试覆盖率 > 90%
- [ ] 集成测试：模拟网络抖动场景
- [ ] 压力测试：1000 次调用，成功率 > 99.8%

---

## 🏗️ 技术设计

### 1. 核心架构

```
┌─────────────────────────────────────┐
│     SnapshotRecorder (调用方)        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       ResilientClient                │
│  (包装器，提供重试与熔断能力)         │
│                                      │
│  ┌────────────┐    ┌──────────────┐ │
│  │ RetryLogic │    │ CircuitBreaker│ │
│  └────────────┘    └──────────────┘ │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Base Client (Mootdx Quotes)     │
└─────────────────────────────────────┘
```

### 2. 断路器状态机

```
        ┌─────────┐
        │ CLOSED  │ ◄─────────── 正常状态
        └────┬────┘
             │
             │ 连续失败 ≥ 5 次
             ▼
        ┌─────────┐
        │  OPEN   │ ◄─────────── 熔断状态（拒绝请求）
        └────┬────┘
             │
             │ 超过 10 分钟
             ▼
        ┌─────────┐
        │HALF_OPEN│ ◄─────────── 尝试恢复
        └────┬────┘
             │
       ┌─────┴─────┐
       │           │
    成功          失败
       │           │
       ▼           ▼
   [CLOSED]     [OPEN]
```

### 3. 重试策略

**指数退避算法**:
```
wait_time = base_delay * (2 ** attempt)

attempt 0: 不等待，直接执行
attempt 1: 等待 1s
attempt 2: 等待 2s
attempt 3: 等待 4s
attempt 4: 等待 8s
attempt 5: 等待 16s
总计: 最多 31 秒
```

---

## 💻 代码实现

### 文件结构
```
src/core/resilience/
├── __init__.py
├── circuit_breaker.py      # 断路器实现
├── retry_policy.py          # 重试策略
└── resilient_client.py      # 弹性客户端包装器
```

### 类设计

#### CircuitState (枚举)
```python
from enum import Enum

class CircuitState(Enum):
    CLOSED = "CLOSED"       # 正常状态
    OPEN = "OPEN"           # 熔断状态
    HALF_OPEN = "HALF_OPEN" # 半开状态
```

#### CircuitBreaker (断路器)
```python
from datetime import datetime, timedelta
from typing import Optional

class CircuitBreaker:
    """断路器实现"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 timeout: int = 600):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count_in_half_open = 0
        
    def record_success(self):
        """记录成功"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count_in_half_open += 1
            if self.success_count_in_half_open >= 2:
                self._close()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self._open()
        elif self.failure_count >= self.failure_threshold:
            self._open()
    
    def can_execute(self) -> bool:
        """判断是否允许执行"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._half_open()
                return True
            return False
        
        # HALF_OPEN 状态
        return True
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置"""
        if self.last_failure_time is None:
            return True
        elapsed = datetime.now() - self.last_failure_time
        return elapsed.total_seconds() >= self.timeout
    
    def _close(self):
        """关闭断路器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count_in_half_open = 0
    
    def _open(self):
        """打开断路器（熔断）"""
        self.state = CircuitState.OPEN
        self.success_count_in_half_open = 0
    
    def _half_open(self):
        """半开状态"""
        self.state = CircuitState.HALF_OPEN
        self.success_count_in_half_open = 0
```

#### RetryPolicy (重试策略)
```python
import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class RetryPolicy:
    """重试策略"""
    
    def __init__(self,
                 max_retries: int = 5,
                 base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retry_count = 0
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数，带重试"""
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                if attempt >= self.max_retries:
                    logger.error(f"Failed after {self.max_retries} retries: {e}")
                    raise
                
                # 计算退避时间
                wait_time = self._calculate_backoff(attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                
                await asyncio.sleep(wait_time)
                self.retry_count += 1
    
    def _calculate_backoff(self, attempt: int) -> float:
        """计算指数退避时间"""
        return self.base_delay * (2 ** attempt)
```

#### ResilientClient (弹性客户端)
```python
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CircuitBreakerOpenError(Exception):
    """断路器开启时抛出的异常"""
    pass

class MaxRetriesExceededError(Exception):
    """重试次数耗尽时抛出的异常"""
    pass

class ResilientClient:
    """弹性客户端包装器"""
    
    def __init__(self,
                 max_retries: int = 5,
                 base_delay: float = 1.0,
                 failure_threshold: int = 5,
                 circuit_timeout: int = 600):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            timeout=circuit_timeout
        )
        self.retry_policy = RetryPolicy(
            max_retries=max_retries,
            base_delay=base_delay
        )
        
        # 统计信息
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retries': 0,
            'circuit_opens': 0
        }
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数，带重试和熔断保护
        
        Args:
            func: 要执行的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitBreakerOpenError: 断路器开启时
            MaxRetriesExceededError: 重试次数耗尽时
        """
        self.stats['total_calls'] += 1
        
        # 检查断路器
        if not self.circuit_breaker.can_execute():
            self.stats['failed_calls'] += 1
            raise CircuitBreakerOpenError(
                f"Circuit breaker is {self.circuit_breaker.state.value}"
            )
        
        # 执行带重试的调用
        try:
            result = await self.retry_policy.execute(func, *args, **kwargs)
            
            # 成功
            self.circuit_breaker.record_success()
            self.stats['successful_calls'] += 1
            return result
            
        except Exception as e:
            # 失败
            self.circuit_breaker.record_failure()
            self.stats['failed_calls'] += 1
            
            if self.circuit_breaker.state == CircuitState.OPEN:
                self.stats['circuit_opens'] += 1
                logger.error(f"Circuit breaker opened after consecutive failures")
            
            raise MaxRetriesExceededError(f"Failed after retries: {e}") from e
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total = self.stats['total_calls']
        if total == 0:
            success_rate = 100.0
        else:
            success_rate = (self.stats['successful_calls'] / total) * 100
        
        return {
            **self.stats,
            'success_rate': f"{success_rate:.2f}%",
            'circuit_state': self.circuit_breaker.state.value
        }
```

---

## 🧪 测试计划

### 单元测试

#### test_circuit_breaker.py
```python
import pytest
from datetime import datetime, timedelta
from src.core.resilience.circuit_breaker import CircuitBreaker, CircuitState

def test_circuit_breaker_initial_state():
    cb = CircuitBreaker()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() == True

def test_circuit_breaker_opens_after_failures():
    cb = CircuitBreaker(failure_threshold=3)
    
    # 记录3次失败
    for _ in range(3):
        cb.record_failure()
    
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() == False

def test_circuit_breaker_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=2, timeout=1)
    
    # 触发熔断
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    
    # 等待超时
    import time
    time.sleep(1.1)
    
    # 应该变为半开
    assert cb.can_execute() == True
    assert cb.state == CircuitState.HALF_OPEN

def test_circuit_breaker_closes_after_success_in_half_open():
    cb = CircuitBreaker(failure_threshold=2, timeout=0)
    
    # 触发熔断并立即进入半开
    cb.record_failure()
    cb.record_failure()
    cb._half_open()
    
    # 连续两次成功应该关闭断路器
    cb.record_success()
    cb.record_success()
    
    assert cb.state == CircuitState.CLOSED
```

#### test_retry_policy.py
```python
import pytest
from src.core.resilience.retry_policy import RetryPolicy

@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt():
    policy = RetryPolicy(max_retries=3)
    
    call_count = 0
    async def func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await policy.execute(func)
    assert result == "success"
    assert call_count == 1

@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    policy = RetryPolicy(max_retries=3, base_delay=0.1)
    
    call_count = 0
    async def func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"
    
    result = await policy.execute(func)
    assert result == "success"
    assert call_count == 3

@pytest.mark.asyncio
async def test_retry_fails_after_max_retries():
    policy = RetryPolicy(max_retries=2, base_delay=0.1)
    
    async def func():
        raise ValueError("Permanent error")
    
    with pytest.raises(ValueError):
        await policy.execute(func)
```

### 集成测试

#### test_resilient_client_integration.py
```python
import pytest
from src.core.resilience.resilient_client import ResilientClient

@pytest.mark.asyncio
async def test_resilient_client_with_transient_failure():
    client = ResilientClient(max_retries=3, base_delay=0.1)
    
    call_count = 0
    async def unstable_api():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("Network timeout")
        return {"data": "success"}
    
    result = await client.execute(unstable_api)
    assert result == {"data": "success"}
    assert call_count == 3
    
    stats = client.get_stats()
    assert stats['successful_calls'] == 1
    assert stats['circuit_state'] == 'CLOSED'
```

---

## 📦 集成方案

### 在 SnapshotRecorder 中使用

```python
from src.core.resilience.resilient_client import ResilientClient

class SnapshotRecorder:
    def __init__(self, pool_manager, storage_path):
        # ... 现有代码
        
        # 创建弹性客户端
        self.resilient = ResilientClient(
            max_retries=5,
            base_delay=1.0,
            failure_threshold=5,
            circuit_timeout=600
        )
    
    async def _fetch_batch_with_resilience(self, batch):
        """带重试保护的批量获取"""
        async def fetch():
            return self.client.quotes(symbol=batch)
        
        try:
            return await self.resilient.execute(fetch)
        except Exception as e:
            logger.error(f"Batch fetch failed after retries: {e}")
            return None  # 降级：跳过这批数据
```

---

## 📊 监控与观测

### 关键指标
- `total_calls`: 总调用次数
- `successful_calls`: 成功次数
- `failed_calls`: 失败次数
- `retries`: 重试次数
- `circuit_opens`: 熔断次数
- `success_rate`: 成功率

### 日志示例
```
2025-11-28 09:30:15 WARNING Attempt 1 failed: ConnectionTimeout. Retrying in 1s...
2025-11-28 09:30:17 WARNING Attempt 2 failed: ConnectionTimeout. Retrying in 2s...
2025-11-28 09:30:20 INFO Retry succeeded on attempt 2
2025-11-28 09:35:42 ERROR Circuit breaker opened after consecutive failures
```

---

## ✅ 完成检查清单

- [ ] 创建 `src/core/resilience/` 目录
- [ ] 实现 `CircuitBreaker` 类
- [ ] 实现 `RetryPolicy` 类
- [ ] 实现 `ResilientClient` 类
- [ ] 编写单元测试（>90% 覆盖率）
- [ ] 编写集成测试
- [ ] 集成到 `SnapshotRecorder`
- [ ] 运行压力测试验证成功率
- [ ] 更新文档和使用示例
- [ ] Code Review 通过

---

**文档版本**: v1.0  
**创建时间**: 2025-11-28  
**预计完成时间**: 2025-12-01
