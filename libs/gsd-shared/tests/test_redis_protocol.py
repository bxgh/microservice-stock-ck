
import pytest
from gsd_shared.redis_protocol import TickJob, TickResult, JobType, JobStatus

def test_tick_job_serialization():
    # Test bool and None conversion
    job = TickJob(
        job_id="test-uuid",
        stock_code="000001",
        type=JobType.POST_MARKET,
        date="20260112",
        market=None, # Should be filtered
        retry_count=0
    )
    
    d = job.to_redis_dict()
    assert "market" not in d
    assert d["job_id"] == "test-uuid"
    assert d["type"] == "post_market"
    # Note: TickJob doesn't have bool yet, but let's assume future proofing
    
def test_tick_result_serialization():
    result = TickResult(
        job_id="test-uuid",
        stock_code="000001",
        date="20260112",
        status=JobStatus.SUCCESS,
        row_count=100,
        check_0925=True, # Must be string in dict
        error_msg=None   # Should be filtered
    )
    
    d = result.to_redis_dict()
    assert d["check_0925"] == "True"
    assert "error_msg" not in d
    assert d["status"] == "success"
    assert d["row_count"] == 100
