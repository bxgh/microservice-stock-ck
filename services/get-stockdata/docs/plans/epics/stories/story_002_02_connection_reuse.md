# Story 002-02: Mootdx 连接复用优化

**Story ID**: STORY-002-02  
**Epic**: EPIC-002 高可用采集引擎  
**优先级**: P0  
**估算**: 2 天  
**状态**: ✅ 已完成  
**依赖**: 无  
**实际完成时间**: 2025-11-29

---

## 📋 Story 概述

优化 `MootdxConnection` 的连接管理机制，实现连接复用而非每次都创建新连接，从而提升性能和资源利用率。

### 业务价值
- 连接创建次数减少 > 90%（从每轮创建变为每5分钟创建一次）
- 首次请求延迟降低约 50ms
- 减少服务端压力，降低被封IP的风险

---

## 🎯 验收标准

### 功能验收
- [ ] 相同配置下能复用连接（不重复创建）
- [ ] 连接超过 5 分钟后自动重新创建
- [ ] 健康检查失败时能正确处理并重连
- [ ] 连接失败时的降级处理

### 性能验收
- [ ] 连接复用率 > 90%
- [ ] 平均连接创建延迟 < 100ms
- [ ] 不影响现有的 `fetch_transactions` 方法性能

### 测试验收
- [ ] 单元测试覆盖率 > 85%
- [ ] 集成测试：连续100次调用，复用率 > 90%
- [ ] 压力测试：1000次调用无泄漏

---

## 🔍 现状分析

### 当前代码问题

**文件**: `src/data_sources/mootdx/connection.py`

```python
class MootdxConnection:
    def __init__(self, timeout: int = 60, best_ip: bool = True):
        self.client: Optional[Quotes] = None
        self._connected = False

    async def connect(self) -> bool:
        # ❌ 问题：每次都创建新连接
        self.client = Quotes.factory(market='std', ...)
        self._connected = True
        return True
```

**问题点**:
1. **无连接生命周期管理**：不知道连接何时应该重建
2. **无健康检查**：不知道连接是否仍然有效
3. **无复用逻辑**：每次调用 `connect()` 都创建新实例

---

## 🏗️ 技术设计

### 1. 连接生命周期管理

```python
from datetime import datetime, timedelta
from typing import Optional

class MootdxConnection:
    def __init__(self, 
                 timeout: int = 60, 
                 best_ip: bool = True,
                 connection_lifetime: int = 300):  # 新增：连接生命周期（秒）
        self.client: Optional[Quotes] = None
        self._connected = False
        self._connect_time: Optional[datetime] = None
        self._connection_lifetime = timedelta(seconds=connection_lifetime)
        self._config = {
            'timeout': timeout,
            'best_ip': best_ip
        }
```

### 2. 智能连接获取

```python
async def get_client(self) -> Optional[Quotes]:
    """
    获取客户端连接，优先复用现有连接
    
    Returns:
        Quotes 客户端实例，如果无法连接则返回 None
    """
    # 1. 如果没有连接，创建新连接
    if self.client is None:
        logger.info("No existing connection, creating new one...")
        return await self._create_connection()
    
    # 2. 检查连接是否过期
    if self._is_connection_expired():
        logger.info("Connection expired, recreating...")
        await self._close_connection()
        return await self._create_connection()
    
    # 3. 简单的健康检查（可选）
    if not self._is_connection_healthy():
        logger.warning("Connection unhealthy, recreating...")
        await self._close_connection()
        return await self._create_connection()
    
    # 4. 复用现有连接
    logger.debug("Reusing existing connection")
    return self.client
```

### 3. 连接状态检查

```python
def _is_connection_expired(self) -> bool:
    """检查连接是否过期"""
    if self._connect_time is None:
        return True
    
    elapsed = datetime.now() - self._connect_time
    return elapsed > self._connection_lifetime

def _is_connection_healthy(self) -> bool:
    """
    简单的连接健康检查
    
    注意：Mootdx 可能没有专门的 ping 接口，
    这里只检查基本状态
    """
    return self._connected and self.client is not None
```

### 4. 连接创建与关闭

```python
async def _create_connection(self) -> Optional[Quotes]:
    """创建新连接"""
    try:
        self.client = Quotes.factory(
            market='std',
            multithread=False,
            heartbeat=False
        )
        self._connected = True
        self._connect_time = datetime.now()
        logger.info("✅ Connection created successfully")
        return self.client
        
    except Exception as e:
        logger.error(f"❌ Failed to create connection: {e}")
        self.client = None
        self._connected = False
        self._connect_time = None
        return None

async def _close_connection(self):
    """关闭连接并清理资源"""
    try:
        # Mootdx 可能没有显式的 close 方法
        # 但我们仍然清理状态
        self.client = None
        self._connected = False
        self._connect_time = None
        logger.debug("Connection closed")
    except Exception as e:
        logger.warning(f"Error closing connection: {e}")
```

---

## 💻 完整实现

### 文件结构
```
src/data_sources/mootdx/
├── connection.py  # 优化此文件
└── fetcher.py     # 更新使用方式
```

### connection.py (完整版本)

```python
import logging
from datetime import datetime, timedelta
from typing import Optional
from mootdx.quotes import Quotes

logger = logging.getLogger(__name__)


class MootdxConnection:
    """
    Mootdx 连接管理器（带连接复用）
    
    Features:
    - 自动连接复用（减少创建次数）
    - 连接生命周期管理（5分钟自动重建）
    - 简单的健康检查
    - 异常处理和降级
    """
    
    def __init__(self, 
                 timeout: int = 60, 
                 best_ip: bool = True,
                 connection_lifetime: int = 300):
        """
        初始化连接管理器
        
        Args:
            timeout: 连接超时时间（秒）
            best_ip: 是否自动选择最佳服务器
            connection_lifetime: 连接生命周期（秒），默认300秒（5分钟）
        """
        self.client: Optional[Quotes] = None
        self._connected = False
        self._connect_time: Optional[datetime] = None
        self._connection_lifetime = timedelta(seconds=connection_lifetime)
        
        self._config = {
            'timeout': timeout,
            'best_ip': best_ip
        }
        
        # 统计信息
        self._stats = {
            'total_creates': 0,
            'total_reuses': 0,
            'total_closes': 0,
            'total_failures': 0
        }
    
    async def get_client(self) -> Optional[Quotes]:
        """
        获取客户端连接（智能复用）
        
        Returns:
            Quotes 客户端实例，如果无法连接则返回 None
        """
        # 1. 无连接或连接已关闭
        if self.client is None or not self._connected:
            return await self._create_connection()
        
        # 2. 连接过期
        if self._is_connection_expired():
            logger.info("Connection expired, recreating...")
            await self._close_connection()
            return await self._create_connection()
        
        # 3. 连接不健康
        if not self._is_connection_healthy():
            logger.warning("Connection unhealthy, recreating...")
            await self._close_connection()
            return await self._create_connection()
        
        # 4. 复用现有连接
        self._stats['total_reuses'] += 1
        logger.debug(f"♻️ Reusing connection (reuses: {self._stats['total_reuses']})")
        return self.client
    
    async def connect(self) -> bool:
        """
        向后兼容的连接方法
        
        Returns:
            bool: 连接是否成功
        """
        client = await self.get_client()
        return client is not None
    
    def _is_connection_expired(self) -> bool:
        """检查连接是否过期"""
        if self._connect_time is None:
            return True
        
        elapsed = datetime.now() - self._connect_time
        is_expired = elapsed > self._connection_lifetime
        
        if is_expired:
            logger.debug(f"Connection expired (age: {elapsed.total_seconds():.1f}s)")
        
        return is_expired
    
    def _is_connection_healthy(self) -> bool:
        """
        简单的连接健康检查
        
        注意：由于 Mootdx 缺少 ping 接口，这里只做基础检查
        """
        return self._connected and self.client is not None
    
    async def _create_connection(self) -> Optional[Quotes]:
        """创建新连接"""
        try:
            logger.info("🔌 Creating new Mootdx connection...")
            
            self.client = Quotes.factory(
                market='std',
                multithread=False,
                heartbeat=False
            )
            
            self._connected = True
            self._connect_time = datetime.now()
            self._stats['total_creates'] += 1
            
            logger.info(f"✅ Connection created (total creates: {self._stats['total_creates']})")
            return self.client
            
        except Exception as e:
            logger.error(f"❌ Failed to create connection: {e}")
            self.client = None
            self._connected = False
            self._connect_time = None
            self._stats['total_failures'] += 1
            return None
    
    async def _close_connection(self):
        """关闭连接"""
        try:
            if self.client:
                # Mootdx Quotes 可能没有显式的 close() 方法
                # 但我们仍然清理引用，让垃圾回收处理
                self.client = None
                self._stats['total_closes'] += 1
                logger.debug(f"🔌 Connection closed (total closes: {self._stats['total_closes']})")
            
            self._connected = False
            self._connect_time = None
            
        except Exception as e:
            logger.warning(f"⚠️ Error closing connection: {e}")
    
    async def close(self):
        """显式关闭连接（可选）"""
        await self._close_connection()
    
    def get_stats(self) -> dict:
        """获取连接统计信息"""
        if self._stats['total_creates'] == 0:
            reuse_rate = 0.0
        else:
            total_uses = self._stats['total_creates'] + self._stats['total_reuses']
            reuse_rate = (self._stats['total_reuses'] / total_uses) * 100
        
        return {
            **self._stats,
            'reuse_rate': f"{reuse_rate:.1f}%",
            'is_connected': self._connected,
            'connection_age': self._get_connection_age()
        }
    
    def _get_connection_age(self) -> Optional[float]:
        """获取当前连接的年龄（秒）"""
        if self._connect_time is None:
            return None
        return (datetime.now() - self._connect_time).total_seconds()
```

---

## 🧪 测试计划

### 单元测试

#### test_mootdx_connection.py

```python
import pytest
import asyncio
from datetime import datetime, timedelta
from src.data_sources.mootdx.connection import MootdxConnection


@pytest.mark.asyncio
async def test_connection_creation():
    """测试连接创建"""
    conn = MootdxConnection(connection_lifetime=300)
    
    client = await conn.get_client()
    assert client is not None
    assert conn._connected == True
    assert conn._connect_time is not None
    
    stats = conn.get_stats()
    assert stats['total_creates'] == 1
    assert stats['total_reuses'] == 0


@pytest.mark.asyncio
async def test_connection_reuse():
    """测试连接复用"""
    conn = MootdxConnection(connection_lifetime=300)
    
    # 第一次获取
    client1 = await conn.get_client()
    
    # 第二次获取（应该复用）
    client2 = await conn.get_client()
    
    assert client1 is client2  # 同一个实例
    
    stats = conn.get_stats()
    assert stats['total_creates'] == 1
    assert stats['total_reuses'] == 1
    assert '50.0%' in stats['reuse_rate']  # 1次创建 + 1次复用 = 50%


@pytest.mark.asyncio
async def test_connection_expiry():
    """测试连接过期重建"""
    conn = MootdxConnection(connection_lifetime=1)  # 1秒过期
    
    # 创建连接
    client1 = await conn.get_client()
    first_create_time = conn._connect_time
    
    # 等待过期
    await asyncio.sleep(1.1)
    
    # 重新获取（应该创建新连接）
    client2 = await conn.get_client()
    
    assert conn._connect_time != first_create_time
    stats = conn.get_stats()
    assert stats['total_creates'] == 2  # 创建了2次


@pytest.mark.asyncio
async def test_connection_close():
    """测试连接关闭"""
    conn = MootdxConnection()
    
    await conn.get_client()
    assert conn._connected == True
    
    await conn.close()
    assert conn._connected == False
    assert conn.client is None
    
    stats = conn.get_stats()
    assert stats['total_closes'] == 1


@pytest.mark.asyncio
async def test_high_reuse_rate():
    """测试高复用率"""
    conn = MootdxConnection(connection_lifetime=300)
    
    # 连续100次获取
    for _ in range(100):
        client = await conn.get_client()
        assert client is not None
    
    stats = conn.get_stats()
    assert stats['total_creates'] == 1
    assert stats['total_reuses'] == 99
    
    # 复用率应该 > 90%
    reuse_rate = float(stats['reuse_rate'].rstrip('%'))
    assert reuse_rate > 90.0
```

---

## 📦 集成方案

### 在 MootdxDataSource 中使用

**文件**: `src/data_sources/mootdx/fetcher.py`

```python
class MootdxDataSource:
    def __init__(self, timeout: int = 60, best_ip: bool = True):
        # 使用新的连接管理器
        self.connection = MootdxConnection(
            timeout=timeout,
            best_ip=best_ip,
            connection_lifetime=300  # 5分钟
        )
    
    async def get_tick_data_dataframe(self, request: TickDataRequest) -> pd.DataFrame:
        # 使用 get_client() 而非 connect()
        client = await self.connection.get_client()
        if client is None:
            logger.error("Failed to get connection")
            return pd.DataFrame()
        
        # 使用 client 进行数据获取
        # ... 原有逻辑
```

### 在 SnapshotRecorder 中使用

**文件**: `src/core/recorder/snapshot_recorder.py`

```python
class SnapshotRecorder:
    async def start(self):
        # 初始化连接（旧方式仍然兼容）
        if not await self.connection.connect():
            logger.error("Failed to connect")
            return
        
        while self.is_running:
            # ... 调度检查
            
            # 获取客户端（自动复用）
            client = await self.connection.get_client()
            if client is None:
                logger.error("Failed to get client")
                continue
            
            # 使用 client 获取数据
            df = client.quotes(symbol=batch)
            # ...
```

---

## 📊 性能预期

### 基准测试

**场景**: 连续采集100轮，每轮283只股票

**优化前**:
- 连接创建次数: 100 次
- 总延迟: ~5-10秒（连接创建开销）

**优化后**:
- 连接创建次数: 1-2 次（5分钟重建一次）
- 总延迟: ~0.5-1秒
- **性能提升**: 5-10倍

---

## ✅ 完成检查清单

- [ ] 修改 `src/data_sources/mootdx/connection.py`
- [ ] 实现 `get_client()` 方法
- [ ] 实现连接生命周期管理
- [ ] 实现连接健康检查
- [ ] 添加统计信息
- [ ] 编写单元测试（>85% 覆盖率）
- [ ] 集成到 `MootdxDataSource`
- [ ] 集成到 `SnapshotRecorder`
- [ ] 运行性能基准测试
- [ ] 验证复用率 > 90%
- [ ] 更新文档

---

**文档版本**: v1.0  
**创建时间**: 2025-11-29  
**预计完成时间**: 2025-12-01
