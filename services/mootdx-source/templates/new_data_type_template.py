"""
新数据类型扩展模板
==================

使用步骤:
1. 复制本文件内容
2. 全局替换以下占位符:
   - NEW_DATA_TYPE -> 您的数据类型名称 (如 DRAGON_TIGER)
   - new_data_type -> 小写蛇形命名 (如 dragon_tiger)
   - NewDataType -> 帕斯卡命名 (如 DragonTiger)
   - source_name -> 数据源名称 (如 akshare, baostock)
3. 按照标记 [TODO] 完成实现
"""

# ==========================================
# 文件 1: service.py 修改
# ==========================================

# [TODO] 步骤 1: 在 ROUTING_TABLE 中添加路由
class MooTDXService(data_source_pb2_grpc.DataSourceServiceServicer):
    ROUTING_TABLE = {
        # ... 现有路由
        
        # 新增: NEW_DATA_TYPE 路由
        data_source_pb2.DATA_TYPE_NEW_DATA_TYPE: RouteConfig(
            handler="_fetch_new_data_type_source_name",
            source_name=DataSource.SOURCE_NAME_API,
            fallback_handler=None  # [TODO] 如需降级，填写降级方法名
        ),
    }
    
    # [TODO] 步骤 2: 实现数据获取方法（添加到云端 API 方法区域）
    # === 云端 API 方法 ===
    
    async def _fetch_new_data_type_source_name(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        source_name: NEW_DATA_TYPE 数据
        
        Args:
            codes: 股票代码列表
                - codes[0]: 主代码
            params: 查询参数
                - param1: 参数1说明
                - param2: 参数2说明 (默认: xxx)
        
        Returns:
            DataFrame 包含 NEW_DATA_TYPE 数据，字段:
                - field1: 字段1说明
                - field2: 字段2说明
        
        Raises:
            ValueError: 当 codes 为空时
        """
        # [TODO] 步骤 2.1: 参数验证
        if not codes:
            raise ValueError("No code specified for NEW_DATA_TYPE")
        
        # [TODO] 步骤 2.2: 提取参数（使用配置默认值）
        code = codes[0]
        param1 = params.get("param1", NewDataTypeDefaults.PARAM1)
        param2 = params.get("param2", NewDataTypeDefaults.PARAM2)
        
        # [TODO] 步骤 2.3: 构建 API 请求
        endpoint = f"/api/v1/new_data_type/{code}"
        query_params = {
            "param1": param1,
            "param2": param2,
        }
        
        # [TODO] 步骤 2.4: 调用数据源客户端
        return await self.cloud_client.fetch_source_name(endpoint, query_params)


# ==========================================
# 文件 2: config.py 修改（如有默认参数）
# ==========================================

# [TODO] 步骤 3: 添加配置常量（可选）
@dataclass(frozen=True)
class NewDataTypeDefaults:
    """NEW_DATA_TYPE 默认参数"""
    PARAM1: str = "default_value1"
    PARAM2: int = 20
    
    @staticmethod
    def get_dynamic_param() -> str:
        """动态计算的参数"""
        return datetime.now().strftime("%Y-%m-%d")


# ==========================================
# 文件 3: tests/test_service.py 修改
# ==========================================

# [TODO] 步骤 4: 添加单元测试
class TestMooTDXService:
    
    @pytest.mark.asyncio
    async def test_fetch_new_data_type_success(self, service):
        """测试 NEW_DATA_TYPE 数据获取成功"""
        # [TODO] 步骤 4.1: 创建 mock 返回数据
        mock_df = pd.DataFrame({
            'code': ['000001', '600519'],
            'field1': ['value1', 'value2'],
            'field2': [100, 200]
        })
        
        # [TODO] 步骤 4.2: Mock 处理方法
        with patch.object(
            service, 
            '_fetch_new_data_type_source_name', 
            return_value=mock_df
        ):
            # [TODO] 步骤 4.3: 构建请求
            request = data_source_pb2.DataRequest(
                type=data_source_pb2.DATA_TYPE_NEW_DATA_TYPE,
                codes=['000001', '600519'],
                params={'param1': 'test_value'}
            )
            
            # [TODO] 步骤 4.4: 执行并验证
            response = await service.FetchData(request, None)
            
            assert response.success is True
            assert response.source_name == DataSource.SOURCE_NAME_API
            assert len(response.json_data) > 0
            
            # 验证返回数据
            data = json.loads(response.json_data)
            assert len(data) == 2
            assert data[0]['code'] == '000001'
    
    @pytest.mark.asyncio
    async def test_fetch_new_data_type_empty_codes(self, service):
        """测试 NEW_DATA_TYPE 空代码列表错误"""
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_NEW_DATA_TYPE,
            codes=[]  # 空列表
        )
        
        response = await service.FetchData(request, None)
        
        assert response.success is False
        assert 'No code specified' in response.error_message
    
    @pytest.mark.asyncio
    async def test_fetch_new_data_type_api_error(self, service):
        """测试 NEW_DATA_TYPE API 错误处理"""
        # Mock API 返回错误
        service.cloud_client.fetch_source_name = AsyncMock(
            side_effect=ConnectionError("API unavailable")
        )
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_NEW_DATA_TYPE,
            codes=['000001']
        )
        
        response = await service.FetchData(request, None)
        
        # 应返回失败，但不崩溃
        assert response.success is False or response.json_data == "[]"


# ==========================================
# 文件 4: cloud_client.py 修改（如需新 API 封装）
# ==========================================

# [TODO] 步骤 5: 添加新 API 方法（如果 source_name 是新数据源）
class CloudAPIClient:
    
    async def fetch_new_source(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        调用 NewSource API
        
        Args:
            endpoint: API 端点 (如 "/api/v1/new_data_type/000001")
            params: 查询参数
        
        Returns:
            pandas DataFrame
        """
        url = f"{self.new_source_url}{endpoint}"
        data = await self._fetch(url, params)
        
        # [TODO] 根据 API 响应格式调整
        if isinstance(data, dict) and 'data' in data:
            data = data['data']
        
        return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])


# ==========================================
# 检查清单
# ==========================================

"""
部署前检查:
[ ] ROUTING_TABLE 已添加新路由
[ ] 实现了 _fetch_xxx 方法
[ ] 添加了配置常量（如有）
[ ] 编写了单元测试（成功+失败场景）
[ ] 方法有完整的 docstring
[ ] 使用了类型提示
[ ] 参数验证完善
[ ] 错误处理和日志记录
[ ] 本地测试通过 (pytest tests/ -v)
[ ] 代码风格符合 PEP 8

部署:
1. docker compose -f docker-compose.microservices.yml build mootdx-source
2. docker compose -f docker-compose.microservices.yml up -d mootdx-source
3. docker logs microservice-stock-mootdx-source --tail 50
4. 发起测试请求验证功能

完成 ✅
"""
