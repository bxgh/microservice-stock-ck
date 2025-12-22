"""Event Bus Tests"""

import asyncio

import pytest

from core.event_bus import EventBus


class TestEventBus:

    @pytest.mark.asyncio
    async def test_pub_sub(self):
        bus = EventBus()
        received = []

        async def _handler(event):
            received.append(event)

        bus.subscribe("test_topic", _handler)
        await bus.publish("test_topic", "hello")
        await asyncio.sleep(0.1) # Wait for async execution

        assert "hello" in received

    @pytest.mark.asyncio
    async def test_sync_handler(self):
        bus = EventBus()
        received = []

        def _handler(event):
            received.append(event)

        bus.subscribe("sync_topic", _handler)
        await bus.publish("sync_topic", "world")
        await asyncio.sleep(0.1)

        assert "world" in received
