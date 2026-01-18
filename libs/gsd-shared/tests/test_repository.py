import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from gsd_shared.validation.result import ValidationResult, ValidationIssue, ValidationLevel
from gsd_shared.repository import AuditRepository

@pytest.fixture
def mock_db_pool():
    pool = MagicMock()
    conn = AsyncMock()
    cur = AsyncMock()
    
    pool.acquire.return_value.__aenter__.return_value = conn
    conn.cursor.return_value.__aenter__.return_value = cur
    
    return pool, conn, cur

@pytest.mark.asyncio
async def test_save_result_success(mock_db_pool):
    pool, conn, cur = mock_db_pool
    repo = AuditRepository(pool)
    
    result = ValidationResult(
        data_type="tick",
        target="600519",
        timestamp=datetime(2026, 1, 18, 10, 0, 0)
    )
    result.add_issue(ValidationIssue(
        dimension="continuity",
        level=ValidationLevel.FAIL,
        message="Missing data"
    ))
    
    # Mock fetching the summary ID
    cur.fetchone.return_value = (1024,)
    
    success = await repo.save_result(result)
    
    assert success is True
    # Verify BEGIN/COMMIT
    cur.execute.assert_any_call("BEGIN")
    cur.execute.assert_any_call("COMMIT")
    
    # Verify summary upsert
    summary_call = [args for args, kwargs in cur.execute.call_args_list if "INSERT INTO data_audit_summaries" in str(args[0])][0]
    assert "tick" in summary_call[1]
    assert "600519" in summary_call[1]
    
    # Verify details refresh
    cur.execute.assert_any_call("DELETE FROM data_audit_details WHERE summary_id = %s", (1024,))
    assert cur.executemany.called

@pytest.mark.asyncio
async def test_save_result_rollback_on_error(mock_db_pool):
    pool, conn, cur = mock_db_pool
    repo = AuditRepository(pool)
    
    cur.executemany.side_effect = Exception("DB Error")
    cur.fetchone.return_value = (1024,)
    
    result = ValidationResult(data_type="test", target="test")
    result.add_issue(ValidationIssue(dimension="d", level=ValidationLevel.FAIL, message="m"))
    
    success = await repo.save_result(result)
    
    assert success is False
    cur.execute.assert_any_call("ROLLBACK")
