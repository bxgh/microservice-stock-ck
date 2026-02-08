"""
Integration tests for PeerSelector
"""
import pytest
import pandas as pd
from src.orchestrator.peer_selector import PeerSelector

@pytest.mark.asyncio
async def test_peer_selector_basic():
    """测试 PeerSelector 基础流程"""
    selector = PeerSelector()
    
    # 测试目标: 688802 (沐曦 - GPGPU芯片)
    target_code = "688802.SH"
    
    result = await selector.select_peers(target_code, max_peers=10)
    
    print(f"Target: {result.target_code}")
    print(f"Industry: {result.target_ths_industry}")
    print(f"Core Concepts: {result.target_core_concepts}")
    print(f"Peers ({len(result.peers)}): {result.peers[:5]}...")  # 只显示前5个
    print(f"Method: {result.selection_method}")
    
    # 基本断言
    assert result.target_code == target_code
    assert isinstance(result.peers, list)
    # Peers 应该不包含自身
    assert target_code not in result.peers

@pytest.mark.asyncio
async def test_peer_selector_industry_only():
    """测试仅行业匹配"""
    selector = PeerSelector()
    
    # 获取目标的行业
    industry = await selector._get_target_industry("688802.SH")
    print(f"Target Industry: {industry}")
    
    # 验证行业匹配
    if industry:
        peers = await selector._match_by_industry("688802.SH", industry)
        print(f"Industry Peers: {len(peers)}")
