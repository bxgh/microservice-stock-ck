#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生产环境就绪性检查脚本
验证系统是否准备好投入生产环境
"""

import asyncio
import sys
import os
import requests
import json
import time
import subprocess
import socket
from datetime import datetime

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

BASE_URL = "http://localhost:8083"

def check_system_resources():
    """检查系统资源"""
    print("=== 检查系统资源 ===")

    try:
        # 检查磁盘空间
        stat = os.statvfs('.')
        free_space_gb = stat.f_bavail * stat.f_frsize / (1024**3)
        print(f"   💾 可用磁盘空间: {free_space_gb:.2f} GB")

        if free_space_gb < 1:
            print("   ⚠️ 磁盘空间不足")
            return False

        # 检查内存使用 (Linux)
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()

            mem_total = 0
            mem_available = 0
            for line in meminfo.split('\n'):
                if 'MemTotal:' in line:
                    mem_total = int(line.split()[1])
                elif 'MemAvailable:' in line:
                    mem_available = int(line.split()[1])

            if mem_total > 0:
                available_gb = mem_available / (1024**2)
                total_gb = mem_total / (1024**2)
                usage_percent = (1 - mem_available / mem_total) * 100

                print(f"   🧠 内存使用: {usage_percent:.1f}% ({available_gb:.1f}GB / {total_gb:.1f}GB)")

                if usage_percent > 90:
                    print("   ⚠️ 内存使用率过高")
                    return False
        except:
            print("   ⚠️ 无法检查内存使用")

        # 检查CPU核心数
        cpu_count = os.cpu_count()
        print(f"   ⚙️ CPU核心数: {cpu_count}")

        if cpu_count < 2:
            print("   ⚠️ CPU核心数较少")

        print("   ✅ 系统资源检查通过")
        return True

    except Exception as e:
        print(f"   ❌ 系统资源检查失败: {e}")
        return False

def check_network_connectivity():
    """检查网络连接"""
    print("\n=== 检查网络连接 ===")

    connectivity_tests = [
        ("本地服务", "localhost", 8083),
        ("百度", "www.baidu.com", 443),
        ("腾讯", "www.qq.com", 443)
    ]

    passed = 0
    for name, host, port in connectivity_tests:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                print(f"   ✅ {name} ({host}:{port}) - 连接成功")
                passed += 1
            else:
                print(f"   ❌ {name} ({host}:{port}) - 连接失败")
        except Exception as e:
            print(f"   ❌ {name} ({host}:{port}) - 异常: {e}")

    print(f"网络连接测试: {passed}/{len(connectivity_tests)} 通过")
    return passed >= 2  # 至少本地服务和1个外网连接

def check_dependencies():
    """检查依赖包"""
    print("\n=== 检查依赖包 ===")

    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "tenacity",
        "mootdx"
    ]

    optional_packages = [
        "redis",
        "nacos-sdk-python",
        "prometheus-client"
    ]

    missing_required = []
    missing_optional = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (必需)")
            missing_required.append(package)

    for package in optional_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ⚠️ {package} (可选)")
            missing_optional.append(package)

    if missing_required:
        print(f"❌ 缺少必需依赖: {missing_required}")
        return False
    elif missing_optional:
        print(f"⚠️ 缺少可选依赖: {missing_optional}")

    print("   ✅ 依赖包检查通过")
    return True

def check_service_configuration():
    """检查服务配置"""
    print("\n=== 检查服务配置 ===")

    config_checks = []

    # 检查环境变量
    env_vars = [
        "PYTHONPATH",
        "LOG_LEVEL"
    ]

    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"   ✅ {var}={value}")
        else:
            print(f"   ⚠️ {var} 未设置")

    # 检查配置文件
    config_files = [
        "src/config.py",
        ".env",
        "requirements.txt"
    ]

    for file_path in config_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path} 存在")
        else:
            print(f"   ⚠️ {file_path} 不存在")

    # 检查服务端口
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ 服务运行正常 (端口8083)")
            config_checks.append(True)
        else:
            print(f"   ❌ 服务响应异常")
            config_checks.append(False)
    except Exception as e:
        print(f"   ❌ 无法连接服务: {e}")
        config_checks.append(False)

    return all(config_checks)

def check_security_settings():
    """检查安全设置"""
    print("\n=== 检查安全设置 ===")

    security_score = 0

    # 检查是否以root运行
    if os.geteuid() == 0:
        print("   ⚠️ 不建议以root用户运行")
    else:
        print("   ✅ 非root用户运行")
        security_score += 1

    # 检查日志级别
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if log_level in ["INFO", "WARNING", "ERROR"]:
        print(f"   ✅ 日志级别: {log_level}")
        security_score += 1
    else:
        print(f"   ⚠️ 日志级别: {log_level} (建议INFO或WARNING)")

    # 检查调试模式
    debug_mode = os.environ.get("DEBUG", "false").lower()
    if debug_mode == "false":
        print("   ✅ 调试模式已关闭")
        security_score += 1
    else:
        print("   ⚠️ 调试模式开启 (生产环境建议关闭)")

    # 检查防火墙 (Linux)
    try:
        result = subprocess.run(['ufw', 'status'],
                              capture_output=True, text=True, timeout=5)
        if "Status: active" in result.stdout:
            print("   ✅ 防火墙已启用")
            security_score += 1
        else:
            print("   ⚠️ 防火墙未启用")
    except:
        print("   ⚠️ 无法检查防火墙状态")

    security_level = "优秀" if security_score >= 3 else "良好" if security_score >= 2 else "需要改进"
    print(f"   🛡️ 安全等级: {security_level} ({security_score}/4)")

    return security_score >= 2

def check_monitoring_setup():
    """检查监控设置"""
    print("\n=== 检查监控设置 ===")

    monitoring_features = []

    # 检查健康检查端点
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            monitoring_features.append("健康检查端点")
            print("   ✅ 健康检查端点可用")
    except:
        print("   ❌ 健康检查端点不可用")

    # 检查API文档
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            monitoring_features.append("API文档")
            print("   ✅ API文档可用")
    except:
        print("   ❌ API文档不可用")

    # 检查日志输出
    if os.path.exists("logs"):
        monitoring_features.append("日志目录")
        print("   ✅ 日志目录存在")
    else:
        print("   ⚠️ 日志目录不存在")

    # 检查Prometheus客户端
    try:
        import prometheus_client
        monitoring_features.append("Prometheus监控")
        print("   ✅ Prometheus客户端可用")
    except:
        print("   ⚠️ Prometheus客户端不可用")

    print(f"监控功能: {len(monitoring_features)}个")
    for feature in monitoring_features:
        print(f"   • {feature}")

    return len(monitoring_features) >= 2

def check_data_persistence():
    """检查数据持久化"""
    print("\n=== 检查数据持久化 ===")

    persistence_score = 0

    # 检查Redis连接
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=5)
        r.ping()
        print("   ✅ Redis连接成功")
        persistence_score += 1
    except:
        print("   ⚠️ Redis连接失败，使用内存缓存")

    # 检查数据目录
    data_dirs = ["data", "results", "cache"]
    for dir_name in data_dirs:
        if os.path.exists(dir_name):
            print(f"   ✅ {dir_name} 目录存在")
            persistence_score += 1
        else:
            print(f"   ⚠️ {dir_name} 目录不存在")

    # 检查数据库连接 (SQLite示例)
    try:
        import sqlite3
        conn = sqlite3.connect(':memory:')
        conn.close()
        print("   ✅ SQLite数据库可用")
        persistence_score += 1
    except:
        print("   ❌ SQLite数据库不可用")

    persistence_level = "完整" if persistence_score >= 4 else "基础" if persistence_score >= 2 else "需要改进"
    print(f"   💾 持久化等级: {persistence_level}")

    return persistence_score >= 2

def generate_production_readiness_report():
    """生成生产就绪性报告"""
    print("\n" + "="*60)
    print("🏭 生产环境就绪性检查报告")
    print("="*60)
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 服务地址: {BASE_URL}")

    # 运行所有检查
    checks = [
        ("系统资源", check_system_resources),
        ("网络连接", check_network_connectivity),
        ("依赖包", check_dependencies),
        ("服务配置", check_service_configuration),
        ("安全设置", check_security_settings),
        ("监控设置", check_monitoring_setup),
        ("数据持久化", check_data_persistence)
    ]

    results = []
    for check_name, check_func in checks:
        print(f"\n🧪 运行检查: {check_name}")
        start_time = time.time()

        try:
            result = check_func()
            execution_time = time.time() - start_time
            results.append({
                'name': check_name,
                'passed': result,
                'time': execution_time
            })
        except Exception as e:
            execution_time = time.time() - start_time
            results.append({
                'name': check_name,
                'passed': False,
                'time': execution_time,
                'error': str(e)
            })

    # 生成总结报告
    total_checks = len(results)
    passed_checks = sum(1 for r in results if r['passed'])
    total_time = sum(r['time'] for r in results)

    print(f"\n{'='*60}")
    print(f"📊 检查总结")
    print(f"{'='*60}")
    print(f"总检查项: {total_checks}")
    print(f"通过项: {passed_checks}")
    print(f"失败项: {total_checks - passed_checks}")
    print(f"通过率: {passed_checks/total_checks:.1%}")
    print(f"总耗时: {total_time:.3f}秒")

    print(f"\n📋 详细结果:")
    for result in results:
        status = '✅ 通过' if result['passed'] else '❌ 失败'
        print(f"   {result['name']}: {status} ({result['time']:.3f}s)")
        if 'error' in result:
            print(f"      错误: {result['error']}")

    # 生产就绪性评估
    readiness_score = passed_checks / total_checks

    if readiness_score >= 0.9:
        readiness_level = "🟢 生产就绪"
        deployment_recommendation = "✅ 可以立即部署到生产环境"
        critical_issues = 0
    elif readiness_score >= 0.7:
        readiness_level = "🟡 基本就绪"
        deployment_recommendation = "⚠️ 修复关键问题后可以部署"
        critical_issues = 2
    else:
        readiness_level = "🔴 需要改进"
        deployment_recommendation = "❌ 不建议部署到生产环境"
        critical_issues = 3

    print(f"\n🎯 生产就绪性: {readiness_level}")
    print(f"📈 就绪评分: {readiness_score:.1%}")
    print(f"🚀 部署建议: {deployment_recommendation}")

    # 部署前任务
    print(f"\n📝 部署前任务:")

    if readiness_score < 1.0:
        failed_checks = [r['name'] for r in results if not r['passed']]
        print(f"   🔧 修复失败的检查项:")
        for check in failed_checks:
            print(f"      • {check}")

    print(f"   🔐 配置生产环境变量")
    print(f"   📊 设置监控和告警")
    print(f"   🗄️ 配置数据备份")
    print(f"   🚀 制定部署计划")
    print(f"   📋 准备回滚方案")

    # 生产环境建议
    print(f"\n💡 生产环境建议:")
    print(f"   • 使用Docker容器化部署")
    print(f"   • 配置负载均衡器")
    print(f"   • 启用日志轮转")
    print(f"   • 设置自动备份")
    print(f"   • 配置监控告警")
    print(f"   • 定期安全更新")
    print(f"   • 性能优化调优")

    if readiness_score >= 0.9:
        print(f"\n🎉 恭喜！系统已准备好部署到生产环境！")
        print(f"   请按照部署计划进行生产环境部署。")
    else:
        print(f"\n⚠️ 请解决上述问题后再进行生产部署。")

    return readiness_score >= 0.7

def main():
    """主函数"""
    print("🏭 开始生产环境就绪性检查")

    success = generate_production_readiness_report()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)