#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能压力测试脚本
测试系统在高负载下的表现
"""

import asyncio
import sys
import os
import time
import threading
import concurrent.futures
import statistics
import requests
import json
from datetime import datetime
from typing import List, Dict, Any

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

BASE_URL = "http://localhost:8083"

class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self.request_times = []
        self.success_count = 0
        self.error_count = 0
        self.errors = []
        self.start_time = None
        self.end_time = None

    def add_request(self, duration: float, success: bool, error: str = None):
        """添加请求记录"""
        self.request_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            if error:
                self.errors.append(error)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.request_times:
            return {}

        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        total_requests = self.success_count + self.error_count

        return {
            'total_requests': total_requests,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.success_count / total_requests if total_requests > 0 else 0,
            'total_duration': total_time,
            'requests_per_second': total_requests / total_time if total_time > 0 else 0,
            'response_times': {
                'avg': statistics.mean(self.request_times),
                'min': min(self.request_times),
                'max': max(self.request_times),
                'p50': statistics.median(self.request_times),
                'p95': self._percentile(self.request_times, 95),
                'p99': self._percentile(self.request_times, 99)
            },
            'error_summary': self._summarize_errors()
        }

    def _percentile(self, data: List[float], percentile: float) -> float:
        """计算百分位数"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _summarize_errors(self) -> Dict[str, int]:
        """总结错误类型"""
        error_counts = {}
        for error in self.errors:
            error_counts[error] = error_counts.get(error, 0) + 1
        return error_counts

def make_request(url: str, method: str = 'GET', data: Dict = None, timeout: int = 30) -> tuple:
    """发起HTTP请求"""
    start_time = time.time()
    success = False
    error = None

    try:
        if method == 'GET':
            response = requests.get(url, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")

        duration = time.time() - start_time

        if response.status_code == 200:
            success = True
        else:
            error = f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        error = "Timeout"
        duration = time.time() - start_time
    except requests.exceptions.ConnectionError:
        error = "Connection Error"
        duration = time.time() - start_time
    except Exception as e:
        error = str(e)
        duration = time.time() - start_time

    return duration, success, error

def test_concurrent_health_checks(concurrent_users: int = 50, duration_seconds: int = 30) -> PerformanceMetrics:
    """测试并发健康检查"""
    print(f"=== 并发健康检查测试 ({concurrent_users} 用户, {duration_seconds} 秒) ===")

    metrics = PerformanceMetrics()
    metrics.start_time = time.time()

    def worker():
        """工作线程"""
        end_time = time.time() + duration_seconds

        while time.time() < end_time:
            duration, success, error = make_request(f"{BASE_URL}/health")
            metrics.add_request(duration, success, error)

            # 短暂休息
            time.sleep(0.1)

    # 启动并发线程
    threads = []
    for _ in range(concurrent_users):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    metrics.end_time = time.time()

    # 打印结果
    stats = metrics.get_stats()
    print(f"   📊 总请求数: {stats['total_requests']}")
    print(f"   ✅ 成功数: {stats['success_count']}")
    print(f"   ❌ 失败数: {stats['error_count']}")
    print(f"   📈 成功率: {stats['success_rate']:.1%}")
    print(f"   ⚡ QPS: {stats['requests_per_second']:.1f}")
    print(f"   ⏱️ 平均响应时间: {stats['response_times']['avg']:.3f}s")
    print(f"   🎯 P95响应时间: {stats['response_times']['p95']:.3f}s")

    return metrics

def test_api_endpoints_load(endpoints: List[Dict], total_requests: int = 1000) -> PerformanceMetrics:
    """测试API端点负载"""
    print(f"=== API端点负载测试 ({total_requests} 请求) ===")

    metrics = PerformanceMetrics()
    metrics.start_time = time.time()

    def single_request(endpoint: Dict):
        """单个请求"""
        url = f"{BASE_URL}{endpoint['path']}"
        duration, success, error = make_request(
            url,
            endpoint.get('method', 'GET'),
            endpoint.get('data')
        )
        metrics.add_request(duration, success, error)

    # 使用线程池进行并发请求
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # 循环发送请求到不同端点
        futures = []
        for i in range(total_requests):
            endpoint = endpoints[i % len(endpoints)]
            future = executor.submit(single_request, endpoint)
            futures.append(future)

        # 等待所有请求完成
        concurrent.futures.wait(futures)

    metrics.end_time = time.time()

    # 打印结果
    stats = metrics.get_stats()
    print(f"   📊 总请求数: {stats['total_requests']}")
    print(f"   ✅ 成功数: {stats['success_count']}")
    print(f"   ❌ 失败数: {stats['error_count']}")
    print(f"   📈 成功率: {stats['success_rate']:.1%}")
    print(f"   ⚡ QPS: {stats['requests_per_second']:.1f}")
    print(f"   ⏱️ 平均响应时间: {stats['response_times']['avg']:.3f}s")
    print(f"   🎯 P95响应时间: {stats['response_times']['p95']:.3f}s")

    if stats['error_summary']:
        print(f"   📋 错误统计:")
        for error, count in stats['error_summary'].items():
            print(f"      • {error}: {count}")

    return metrics

def test_strategy_engine_performance() -> PerformanceMetrics:
    """测试策略引擎性能"""
    print("=== 策略引擎性能测试 ===")

    metrics = PerformanceMetrics()

    try:
        from services.guaranteed_success_strategy import guaranteed_strategy_instance

        # 测试交易所判断性能
        test_symbols = []
        for prefix in ['000', '002', '300', '600', '688', '430']:
            for i in range(100):
                test_symbols.append(f"{prefix}{i:04d}")

        print(f"   🏢 测试交易所判断 ({len(test_symbols)} 个股票代码)")

        start_time = time.time()
        for symbol in test_symbols:
            start = time.time()
            market = guaranteed_strategy_instance._determine_market(symbol)
            duration = time.time() - start
            metrics.add_request(duration, True)

        total_time = time.time() - start_time
        metrics.end_time = time.time()

        stats = metrics.get_stats()
        print(f"   ⚡ QPS: {len(test_symbols)/total_time:.1f}")
        print(f"   ⏱️ 平均处理时间: {stats['response_times']['avg']*1000:.3f}ms")
        print(f"   🎯 P95处理时间: {stats['response_times']['p95']*1000:.3f}ms")

    except Exception as e:
        print(f"   ❌ 策略引擎测试失败: {e}")
        for _ in range(1000):
            metrics.add_request(0.001, False, "Engine Error")

    return metrics

def test_data_model_performance() -> PerformanceMetrics:
    """测试数据模型性能"""
    print("=== 数据模型性能测试 ===")

    metrics = PerformanceMetrics()

    try:
        from models.guaranteed_strategy_models import SuccessResult, SearchStep

        print(f"   📊 测试数据模型创建 (1000 个实例)")

        start_time = time.time()
        for i in range(1000):
            model_start = time.time()

            step = SearchStep(
                step_id=i+1,
                description=f"测试步骤{i+1}",
                start_pos=4000 + i,
                offset=500,
                found_0925=True if i % 2 == 0 else False,
                earliest_time="09:25:00",
                record_count=100 + i,
                execution_time=0.1 + i * 0.001
            )

            result = SuccessResult(
                symbol=f"00000{i % 10}",
                name=f"测试股票{i % 10}",
                success=True,
                earliest_time="09:25:00",
                latest_time="15:00:00",
                record_count=5000 + i,
                strategy_used="万科A原成功",
                execution_time=15.8 + i * 0.01,
                target_achieved=True,
                market="SZ",
                date="20251119",
                data_source="tongdaxin",
                retry_count=0,
                search_steps=[step]
            )

            duration = time.time() - model_start
            metrics.add_request(duration, True)

        total_time = time.time() - start_time
        metrics.end_time = time.time()

        stats = metrics.get_stats()
        print(f"   ⚡ 创建速度: {1000/total_time:.1f} 模型/秒")
        print(f"   ⏱️ 平均创建时间: {stats['response_times']['avg']*1000:.3f}ms")
        print(f"   🎯 P95创建时间: {stats['response_times']['p95']*1000:.3f}ms")

    except Exception as e:
        print(f"   ❌ 数据模型测试失败: {e}")
        for _ in range(1000):
            metrics.add_request(0.001, False, "Model Error")

    return metrics

def test_memory_usage():
    """测试内存使用"""
    print("=== 内存使用测试 ===")

    try:
        import psutil
        import gc

        process = psutil.Process()

        # 记录初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"   🧠 初始内存: {initial_memory:.2f} MB")

        # 创建大量对象
        objects = []
        for i in range(10000):
            step = {
                'step_id': i,
                'description': f'测试步骤{i}',
                'start_pos': 4000 + i,
                'offset': 500,
                'found_0925': i % 2 == 0
            }
            objects.append(step)

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"   📈 峰值内存: {peak_memory:.2f} MB")
        print(f"   📊 内存增长: {peak_memory - initial_memory:.2f} MB")

        # 清理对象
        objects.clear()
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"   🧹 清理后内存: {final_memory:.2f} MB")
        print(f"   🔄 内存回收: {peak_memory - final_memory:.2f} MB")

        # 评估内存使用
        memory_growth = peak_memory - initial_memory
        if memory_growth < 50:
            print("   ✅ 内存使用良好")
            return True
        elif memory_growth < 100:
            print("   ⚠️ 内存使用一般")
            return True
        else:
            print("   ❌ 内存使用过高")
            return False

    except ImportError:
        print("   ⚠️ psutil未安装，跳过内存测试")
        return True
    except Exception as e:
        print(f"   ❌ 内存测试失败: {e}")
        return False

def generate_performance_report():
    """生成性能测试报告"""
    print("\n" + "="*60)
    print("⚡ 性能压力测试报告")
    print("="*60)
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 服务地址: {BASE_URL}")

    # 运行所有性能测试
    tests = [
        ("策略引擎性能", test_strategy_engine_performance),
        ("数据模型性能", test_data_model_performance),
        ("内存使用", test_memory_usage)
    ]

    # API端点列表
    api_endpoints = [
        {"path": "/health", "method": "GET"},
        {"path": "/api/v1/stocks/test", "method": "GET"},
        {"path": "/api/v1/ticks/test", "method": "GET"},
        {"path": "/api/v1/strategy/test", "method": "GET"},
        {"path": "/docs", "method": "GET"}
    ]

    # 并发测试
    print(f"\n🔥 开始性能压力测试...")

    # 1. 并发健康检查
    health_metrics = test_concurrent_health_checks(concurrent_users=20, duration_seconds=10)

    # 2. API端点负载测试
    api_metrics = test_api_endpoints_load(api_endpoints, total_requests=500)

    # 3. 组件性能测试
    component_results = []
    for test_name, test_func in tests:
        print(f"\n🧪 运行测试: {test_name}")
        start_time = time.time()

        try:
            metrics = test_func()
            component_results.append({
                'name': test_name,
                'passed': True,
                'time': time.time() - start_time,
                'metrics': metrics
            })
        except Exception as e:
            component_results.append({
                'name': test_name,
                'passed': False,
                'time': time.time() - start_time,
                'error': str(e)
            })

    # 生成总结报告
    print(f"\n{'='*60}")
    print(f"📊 性能测试总结")
    print(f"{'='*60}")

    # 健康检查结果
    health_stats = health_metrics.get_stats()
    print(f"🏥 并发健康检查:")
    print(f"   QPS: {health_stats['requests_per_second']:.1f}")
    print(f"   成功率: {health_stats['success_rate']:.1%}")
    print(f"   平均响应: {health_stats['response_times']['avg']:.3f}s")
    print(f"   P95响应: {health_stats['response_times']['p95']:.3f}s")

    # API负载测试结果
    api_stats = api_metrics.get_stats()
    print(f"\n🌐 API负载测试:")
    print(f"   QPS: {api_stats['requests_per_second']:.1f}")
    print(f"   成功率: {api_stats['success_rate']:.1%}")
    print(f"   平均响应: {api_stats['response_times']['avg']:.3f}s")
    print(f"   P95响应: {api_stats['response_times']['p95']:.3f}s")

    # 组件测试结果
    print(f"\n🔧 组件性能测试:")
    for result in component_results:
        status = '✅ 通过' if result['passed'] else '❌ 失败'
        print(f"   {result['name']}: {status} ({result['time']:.3f}s)")
        if not result['passed']:
            print(f"      错误: {result['error']}")

    # 性能评级
    performance_score = 0
    max_score = 4

    # 评估QPS
    if api_stats['requests_per_second'] >= 100:
        performance_score += 1
        print(f"\n⚡ QPS性能: ✅ 优秀 ({api_stats['requests_per_second']:.1f})")
    elif api_stats['requests_per_second'] >= 50:
        performance_score += 0.5
        print(f"\n⚡ QPS性能: 🟡 良好 ({api_stats['requests_per_second']:.1f})")
    else:
        print(f"\n⚡ QPS性能: 🔴 需要改进 ({api_stats['requests_per_second']:.1f})")

    # 评估响应时间
    if api_stats['response_times']['p95'] <= 0.1:
        performance_score += 1
        print(f"⏱️ 响应时间: ✅ 优秀 (P95: {api_stats['response_times']['p95']:.3f}s)")
    elif api_stats['response_times']['p95'] <= 0.5:
        performance_score += 0.5
        print(f"⏱️ 响应时间: 🟡 良好 (P95: {api_stats['response_times']['p95']:.3f}s)")
    else:
        print(f"⏱️ 响应时间: 🔴 需要改进 (P95: {api_stats['response_times']['p95']:.3f}s)")

    # 评估成功率
    if api_stats['success_rate'] >= 0.99:
        performance_score += 1
        print(f"📈 成功率: ✅ 优秀 ({api_stats['success_rate']:.1%})")
    elif api_stats['success_rate'] >= 0.95:
        performance_score += 0.5
        print(f"📈 成功率: 🟡 良好 ({api_stats['success_rate']:.1%})")
    else:
        print(f"📈 成功率: 🔴 需要改进 ({api_stats['success_rate']:.1%})")

    # 评估组件测试
    component_passed = sum(1 for r in component_results if r['passed'])
    if component_passed == len(component_results):
        performance_score += 1
        print(f"🔧 组件性能: ✅ 优秀 ({component_passed}/{len(component_results)})")
    elif component_passed >= len(component_results) * 0.8:
        performance_score += 0.5
        print(f"🔧 组件性能: 🟡 良好 ({component_passed}/{len(component_results)})")
    else:
        print(f"🔧 组件性能: 🔴 需要改进 ({component_passed}/{len(component_results)})")

    # 最终评级
    performance_percent = performance_score / max_score
    if performance_percent >= 0.9:
        performance_grade = "A+ 优秀"
        deployment_ready = "✅ 生产就绪"
    elif performance_percent >= 0.7:
        performance_grade = "A 良好"
        deployment_ready = "⚠️ 基本就绪"
    elif performance_percent >= 0.5:
        performance_grade = "B 合格"
        deployment_ready = "🔧 需要优化"
    else:
        performance_grade = "C 需要改进"
        deployment_ready = "❌ 不建议部署"

    print(f"\n🎯 性能评级: {performance_grade} ({performance_percent:.1%})")
    print(f"🚀 部署状态: {deployment_ready}")

    # 性能建议
    print(f"\n💡 性能优化建议:")
    if api_stats['requests_per_second'] < 100:
        print(f"   • 增加并发处理能力")
        print(f"   • 优化数据库查询")
        print(f"   • 使用连接池")

    if api_stats['response_times']['p95'] > 0.1:
        print(f"   • 启用缓存机制")
        print(f"   • 优化API响应逻辑")
        print(f"   • 减少外部调用")

    if api_stats['success_rate'] < 0.99:
        print(f"   • 增强错误处理")
        print(f"   • 改善网络稳定性")
        print(f"   • 增加重试机制")

    if performance_percent >= 0.9:
        print(f"\n🎉 恭喜！系统性能表现优秀！")
        print(f"   系统已准备好处理生产环境负载。")
    elif performance_percent >= 0.7:
        print(f"\n👍 系统性能表现良好！")
        print(f"   建议进行一些优化后部署到生产环境。")
    else:
        print(f"\n⚠️ 系统性能需要改进！")
        print(f"   请按照建议进行优化后再考虑生产部署。")

    return performance_percent >= 0.7

def main():
    """主函数"""
    print("⚡ 开始性能压力测试")

    success = generate_performance_report()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)