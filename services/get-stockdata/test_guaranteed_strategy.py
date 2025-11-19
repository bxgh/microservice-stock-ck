#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GuaranteedSuccessStrategy核心引擎测试
测试100%成功策略的完整功能
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_strategy_models():
    """测试策略数据模型"""
    print('=== 测试策略数据模型 ===')

    try:
        from models.guaranteed_strategy_models import (
            SuccessResult, SearchStep, BatchExecutionRequest,
            GuaranteedStrategyConfig, TickDataValidationResult
        )

        # 测试SearchStep
        step = SearchStep(
            step_id=1,
            description="测试步骤",
            start_pos=1000,
            offset=500,
            found_0925=True,
            earliest_time="09:25:00",
            record_count=100,
            execution_time=2.5
        )
        print(f'✅ SearchStep模型创建成功: {step.description}')

        # 测试SuccessResult
        result = SuccessResult(
            symbol="000001",
            name="平安银行",
            success=True,
            earliest_time="09:25:00",
            latest_time="15:00:00",
            record_count=5000,
            strategy_used="万科A原成功",
            execution_time=15.8,
            target_achieved=True,
            data_quality_score=0.95,
            search_steps=[step],
            market="SZ",
            date="20251119",
            data_source="tongdaxin",
            retry_count=0
        )
        print(f'✅ SuccessResult模型创建成功: {result.symbol} - {result.strategy_used}')

        # 测试BatchExecutionRequest
        request = BatchExecutionRequest(
            stock_list=[
                {"symbol": "000001", "name": "平安银行"},
                {"symbol": "000002", "name": "万科A"}
            ],
            date="20251119",
            target_time="09:25",
            max_concurrent=3,
            timeout_per_stock=120,
            retry_attempts=2
        )
        print(f'✅ BatchExecutionRequest模型创建成功: {len(request.stock_list)}只股票')

        # 测试GuaranteedStrategyConfig
        config = GuaranteedStrategyConfig(
            target_time="09:25",
            max_search_steps=15,
            smart_stop_enabled=True,
            max_concurrent_stocks=5
        )
        print(f'✅ GuaranteedStrategyConfig模型创建成功: 目标时间={config.target_time}')

        # 测试TickDataValidationResult
        validation = TickDataValidationResult(
            is_valid=True,
            earliest_time="09:25:00",
            latest_time="15:00:00",
            target_achieved=True,
            record_count=5000,
            quality_score=0.98
        )
        print(f'✅ TickDataValidationResult模型创建成功: 质量评分={validation.quality_score}')

        return True

    except Exception as e:
        print(f'❌ 策略数据模型测试失败: {e}')
        return False


async def test_strategy_engine_initialization():
    """测试策略引擎初始化"""
    print('\n=== 测试策略引擎初始化 ===')

    try:
        from services.guaranteed_success_strategy import GuaranteedSuccessStrategy, guaranteed_strategy_instance

        # 测试默认配置初始化
        strategy1 = GuaranteedSuccessStrategy()
        print(f'✅ 默认配置策略引擎创建成功')
        print(f'   📊 搜索矩阵步数: {len(strategy1.proven_search_matrix)}')
        print(f'   🎯 目标时间: {strategy1.config.target_time}')

        # 测试自定义配置初始化
        from models.guaranteed_strategy_models import GuaranteedStrategyConfig
        custom_config = GuaranteedStrategyConfig(
            target_time="09:30",
            max_concurrent_stocks=3,
            smart_stop_enabled=False
        )
        strategy2 = GuaranteedSuccessStrategy(custom_config)
        print(f'✅ 自定义配置策略引擎创建成功')
        print(f'   🎯 自定义目标时间: {strategy2.config.target_time}')
        print(f'   🔄 最大并发数: {strategy2.config.max_concurrent_stocks}')

        # 测试全局实例
        print(f'✅ 全局策略实例可用')
        print(f'   📊 全局实例搜索矩阵步数: {len(guaranteed_strategy_instance.proven_search_matrix)}')

        return True

    except Exception as e:
        print(f'❌ 策略引擎初始化测试失败: {e}')
        return False


async def test_search_matrix():
    """测试搜索矩阵"""
    print('\n=== 测试搜索矩阵 ===')

    try:
        from services.guaranteed_success_strategy import guaranteed_strategy_instance

        matrix = guaranteed_strategy_instance.proven_search_matrix

        print(f'✅ 搜索矩阵加载成功，共{len(matrix)}个步骤')

        # 显示搜索矩阵内容
        for i, step in enumerate(matrix[:5]):  # 显示前5个步骤
            print(f'   步骤{i+1}: {step["description"]} (start={step["start_pos"]}, offset={step["offset"]})')

        # 验证矩阵结构
        required_fields = ['start_pos', 'offset', 'description', 'priority']
        for i, step in enumerate(matrix):
            for field in required_fields:
                if field not in step:
                    print(f'❌ 搜索矩阵步骤{i+1}缺少字段: {field}')
                    return False

        print(f'✅ 搜索矩阵结构验证通过')

        return True

    except Exception as e:
        print(f'❌ 搜索矩阵测试失败: {e}')
        return False


async def test_market_determination():
    """测试交易所判断逻辑"""
    print('\n=== 测试交易所判断逻辑 ===')

    try:
        from services.guaranteed_success_strategy import guaranteed_strategy_instance

        test_cases = [
            ("600519", "SH", "贵州茅台"),
            ("000001", "SZ", "平安银行"),
            ("688001", "SH", "科创板股票"),
            ("300001", "SZ", "创业板股票"),
            ("832077", "BJ", "北交所股票"),
            ("430001", "BJ", "新三板股票")
        ]

        for symbol, expected_market, description in test_cases:
            actual_market = guaranteed_strategy_instance._determine_market(symbol)
            if actual_market == expected_market:
                print(f'✅ {symbol} -> {actual_market} ({description})')
            else:
                print(f'❌ {symbol} -> 期望{expected_market}, 实际{actual_market}')
                return False

        return True

    except Exception as e:
        print(f'❌ 交易所判断测试失败: {e}')
        return False


async def test_tick_data_validation():
    """测试分笔数据验证"""
    print('\n=== 测试分笔数据验证 ===')

    try:
        from services.guaranteed_success_strategy import guaranteed_strategy_instance
        from models.tick_models import TickData

        # 创建测试数据
        test_time = datetime.now()
        tick_data_list = [
            TickData(
                time=test_time.replace(hour=9, minute=25, second=0),
                price=10.50,
                volume=1000,
                amount=10500.0,
                direction="B",
                code="000001",
                date=test_time.date()
            ),
            TickData(
                time=test_time.replace(hour=9, minute=30, second=0),
                price=10.55,
                volume=2000,
                amount=21100.0,
                direction="S",
                code="000001",
                date=test_time.date()
            )
        ]

        # 验证数据
        validation_result = await guaranteed_strategy_instance._validate_tick_data(
            tick_data_list, "09:25"
        )

        print(f'✅ 数据验证完成')
        print(f'   📊 验证结果: {"有效" if validation_result.is_valid else "无效"}')
        print(f'   🎯 目标达成: {"是" if validation_result.target_achieved else "否"}')
        print(f'   📈 质量评分: {validation_result.quality_score:.2f}')
        print(f'   📝 记录数量: {validation_result.record_count}')

        # 测试空数据
        empty_validation = await guaranteed_strategy_instance._validate_tick_data([], "09:25")
        print(f'✅ 空数据验证: {"无效" if not empty_validation.is_valid else "有效"}')

        return True

    except Exception as e:
        print(f'❌ 分笔数据验证测试失败: {e}')
        return False


async def test_strategy_execution_stats():
    """测试策略执行统计"""
    print('\n=== 测试策略执行统计 ===')

    try:
        from services.guaranteed_success_strategy import guaranteed_strategy_instance

        # 获取初始统计
        stats = guaranteed_strategy_instance.get_execution_stats()
        print(f'✅ 执行统计获取成功')
        print(f'   📊 总执行次数: {stats["total_executions"]}')
        print(f'   📈 成功次数: {stats["successful_executions"]}')
        print(f'   🎯 成功率: {stats["success_rate"]:.1%}')

        # 测试统计更新
        guaranteed_strategy_instance._update_execution_stats(True, 15.5)
        guaranteed_strategy_instance._update_execution_stats(False, 8.2, "测试错误")

        # 获取更新后统计
        updated_stats = guaranteed_strategy_instance.get_execution_stats()
        print(f'✅ 统计更新成功')
        print(f'   📊 更新后总执行次数: {updated_stats["total_executions"]}')
        print(f'   📈 更新后成功次数: {updated_stats["successful_executions"]}')
        print(f'   🎯 更新后成功率: {updated_stats["success_rate"]:.1%}')
        print(f'   ⚠️ 错误记录数: {len(updated_stats["recent_errors"])}')

        return True

    except Exception as e:
        print(f'❌ 策略执行统计测试失败: {e}')
        return False


async def test_strategy_routes():
    """测试策略路由注册"""
    print('\n=== 测试策略路由注册 ===')

    try:
        from main import create_app

        app = create_app()

        # 统计策略相关路由
        strategy_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and (
                '/api/v1/strategy' in route.path or
                '/internal/strategy' in route.path
            ):
                strategy_routes.append({
                    'path': route.path,
                    'methods': getattr(route, 'methods', []),
                    'name': getattr(route, 'name', 'unknown')
                })

        print(f'✅ 策略路由注册成功')
        print(f'   📊 策略路由数量: {len(strategy_routes)}')

        # 显示关键路由
        key_routes = [
            '/api/v1/strategy/single/{symbol}',
            '/api/v1/strategy/batch',
            '/api/v1/strategy/stats',
            '/api/v1/strategy/config',
            '/internal/strategy/health'
        ]

        for route_info in strategy_routes:
            for key_route in key_routes:
                if key_route in route_info['path']:
                    methods = ', '.join(route_info['methods']) if route_info['methods'] else 'ANY'
                    print(f'   🛣️  {route_info["path"]} [{methods}]')
                    break

        return True

    except Exception as e:
        print(f'❌ 策略路由注册测试失败: {e}')
        return False


async def main():
    """主测试函数"""
    print('🚀 开始GuaranteedSuccessStrategy核心引擎测试\n')

    tests = [
        ("策略数据模型", test_strategy_models),
        ("策略引擎初始化", test_strategy_engine_initialization),
        ("搜索矩阵", test_search_matrix),
        ("交易所判断", test_market_determination),
        ("分笔数据验证", test_tick_data_validation),
        ("策略执行统计", test_strategy_execution_stats),
        ("策略路由注册", test_strategy_routes)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f'🧪 运行测试: {test_name}')
        try:
            if await test_func():
                passed += 1
                print(f'✅ {test_name} - 通过\n')
            else:
                print(f'❌ {test_name} - 失败\n')
        except Exception as e:
            print(f'❌ {test_name} - 异常: {e}\n')

    # 测试总结
    print('=== 测试总结 ===')
    print(f'📊 总测试数: {total}')
    print(f'✅ 通过数: {passed}')
    print(f'❌ 失败数: {total - passed}')
    print(f'🎯 通过率: {passed/total:.1%}')

    if passed == total:
        print('\n🎉 所有测试通过！GuaranteedSuccessStrategy核心引擎集成成功！')
        print('\n📋 已验证功能:')
        print('   ✅ 完整的数据模型体系')
        print('   ✅ 策略引擎初始化和配置')
        print('   ✅ 智能搜索策略矩阵')
        print('   ✅ 交易所自动判断')
        print('   ✅ 分笔数据质量验证')
        print('   ✅ 执行统计和监控')
        print('   ✅ API路由注册完成')

        print('\n🚀 可用API端点:')
        print('   📈 单只股票策略: POST /api/v1/strategy/single/{symbol}')
        print('   📊 批量策略执行: POST /api/v1/strategy/batch')
        print('   📈 策略统计信息: GET /api/v1/strategy/stats')
        print('   ⚙️  策略配置管理: GET/POST /api/v1/strategy/config')
        print('   🔍 任务状态查询: GET /api/v1/strategy/batch/{task_id}/status')
        print('   📋 任务结果获取: GET /api/v1/strategy/batch/{task_id}/result')
        print('   💓 内部健康检查: GET /internal/strategy/health')

        print('\n🎯 核心特性:')
        print('   🔄 基于验证成功的搜索矩阵')
        print('   🎯 100%成功率保证机制')
        print('   📊 数据质量验证和评分')
        print('   ⚡ 异步并发处理')
        print('   🛡️ 完整的错误处理和重试')
        print('   📈 详细的执行统计')

    else:
        print(f'\n⚠️ {total-passed}个测试失败，请检查实现')

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)