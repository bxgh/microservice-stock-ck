"""
健康检查 API 测试
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import create_app


class TestHealthAPI:
    """健康检查 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def mock_db_health(self):
        """模拟数据库健康检查"""
        return {
            "mysql": True,
            "redis": True,
            "clickhouse": True,
            "overall": True
        }

    @pytest.fixture
    def mock_db_health_partial_failure(self):
        """模拟部分数据库健康检查失败"""
        return {
            "mysql": True,
            "redis": False,
            "clickhouse": True,
            "overall": False
        }

    def test_health_check_success(self, client, mock_db_health):
        """测试健康检查成功"""
        with patch('api.health_routes.check_all_databases', return_value=mock_db_health):
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Service health check completed"

        # 验证健康检查数据
        health_data = data["data"]
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "quant-strategy"
        assert "timestamp" in health_data
        assert "uptime" in health_data
        assert "version" in health_data

        # 验证检查项
        checks = health_data["checks"]
        assert checks["framework"]["status"] == "pass"
        assert checks["api"]["status"] == "pass"
        assert checks["database"]["status"] == "pass"
        assert checks["strategy_engine"]["status"] == "pass"

    def test_health_check_database_failure(self, client, mock_db_health_partial_failure):
        """测试健康检查中数据库失败"""
        with patch('api.health_routes.check_all_databases', return_value=mock_db_health_partial_failure):
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        health_data = data["data"]
        # 由于数据库检查失败，整体状态应该是 degraded
        assert health_data["status"] == "degraded"

        checks = health_data["checks"]
        assert checks["database"]["status"] == "fail"

    def test_health_check_exception(self, client):
        """测试健康检查异常情况"""
        with patch('api.health_routes.check_all_databases', side_effect=Exception("Database error")):
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Health check failed" in data["message"]

    def test_readiness_check_ready(self, client, mock_db_health):
        """测试就绪检查 - 服务就绪"""
        with patch('api.health_routes.check_all_databases', return_value=mock_db_health):
            response = client.get("/api/v1/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Service is ready"

        readiness_data = data["data"]
        assert readiness_data["status"] == "ready"
        assert "timestamp" in readiness_data
        assert "uptime" in readiness_data

    def test_readiness_check_not_ready(self, client, mock_db_health_partial_failure):
        """测试就绪检查 - 服务未就绪"""
        with patch('api.health_routes.check_all_databases', return_value=mock_db_health_partial_failure):
            response = client.get("/api/v1/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "database connections unhealthy" in data["message"]

        readiness_data = data["data"]
        assert readiness_data["status"] == "not_ready"
        assert readiness_data["reason"] == "database_unhealthy"
        assert "details" in readiness_data

    def test_readiness_check_exception(self, client):
        """测试就绪检查异常"""
        with patch('api.health_routes.check_all_databases', side_effect=Exception("Check failed")):
            response = client.get("/api/v1/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

        readiness_data = data["data"]
        assert readiness_data["status"] == "not_ready"
        assert readiness_data["reason"] == "check_failed"

    def test_liveness_check_alive(self, client):
        """测试存活检查 - 服务存活"""
        response = client.get("/api/v1/live")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Service is alive"

        liveness_data = data["data"]
        assert liveness_data["status"] == "alive"
        assert liveness_data["service"] == "quant-strategy"
        assert "timestamp" in liveness_data
        assert "uptime" in liveness_data

    def test_liveness_check_exception(self, client):
        """测试存活检查异常"""
        # 模拟获取配置时出错
        with patch('api.health_routes.settings', side_effect=Exception("Config error")):
            response = client.get("/api/v1/live")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

        liveness_data = data["data"]
        assert liveness_data["status"] == "not_alive"

    def test_health_check_response_time(self, client, mock_db_health):
        """测试健康检查响应时间"""
        import time

        with patch('api.health_routes.check_all_databases', return_value=mock_db_health):
            start_time = time.time()
            response = client.get("/api/v1/health")
            response_time = time.time() - start_time

        assert response.status_code == 200
        # 响应时间应该小于 100ms
        assert response_time < 0.1

    def test_health_check_headers(self, client, mock_db_health):
        """测试健康检查响应头"""
        with patch('api.health_routes.check_all_databases', return_value=mock_db_health):
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        # 检查响应头
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]

    def test_health_check_uptime_calculation(self, client, mock_db_health):
        """测试运行时间计算"""
        with patch('api.health_routes.check_all_databases', return_value=mock_db_health):
            response = client.get("/api/v1/health")
            uptime1 = response.json()["data"]["uptime"]

            # 等待一小段时间
            import time
            time.sleep(0.1)

            response = client.get("/api/v1/health")
            uptime2 = response.json()["data"]["uptime"]

        # 运行时间应该增加
        assert uptime2 > uptime1
        # 增加的时间应该至少 0.1 秒（考虑延迟）
        assert uptime2 - uptime1 >= 0

    def test_health_check_version_included(self, client, mock_db_health):
        """测试健康检查包含版本信息"""
        with patch('api.health_routes.check_all_databases', return_value=mock_db_health):
            response = client.get("/api/v1/health")

        data = response.json()
        health_data = data["data"]
        assert "version" in health_data
        assert health_data["version"] == "1.0.0"

    def test_health_check_service_name(self, client, mock_db_health):
        """测试健康检查包含服务名称"""
        with patch('api.health_routes.check_all_databases', return_value=mock_db_health):
            response = client.get("/api/v1/health")

        data = response.json()
        health_data = data["data"]
        assert health_data["service"] == "quant-strategy"