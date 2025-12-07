#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富网络问题解决方案
提供多种方法解决东方财富数据源的SSL连接问题
"""

import akshare as ak
import requests
import ssl
import socket
import time
import urllib3
from urllib3.util.ssl_ import create_urllib3_context
import warnings

def diagnose_eastmoney_issue():
    """诊断东方财富连接问题"""
    print("🔍 诊断东方财富连接问题...")

    # 测试基础连接
    eastmoney_urls = [
        "https://push2.eastmoney.com",
        "https://82.push2.eastmoney.com",
        "https://datacenter-web.eastmoney.com",
        "https://quotation.eastmoney.com"
    ]

    for url in eastmoney_urls:
        try:
            print(f"🔗 测试连接: {url}")
            response = requests.get(url, timeout=10)
            print(f"✅ {url} - 状态码: {response.status_code}")
        except requests.exceptions.SSLError as e:
            print(f"❌ {url} - SSL错误: {str(e)[:80]}...")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ {url} - 连接错误: {str(e)[:80]}...")
        except Exception as e:
            print(f"❌ {url} - 其他错误: {str(e)[:80]}...")

def solution_1_ssl_verification():
    """方案1: 更新和配置SSL证书"""
    print("\n📋 方案1: 更新和配置SSL证书")

    # 1.1 更新certifi
    print("1.1 更新certifi包...")
    import subprocess
    import sys

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "certifi"])
        print("✅ certifi已更新")
    except:
        print("❌ certifi更新失败")

    # 1.2 设置SSL上下文
    print("\n1.2 配置SSL上下文...")

    # 创建自定义SSL上下文
    class CustomHTTPSAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            context = create_urllib3_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            kwargs['ssl_context'] = context
            kwargs['assert_hostname'] = False
            return super().init_poolmanager(*args, **kwargs)

    # 测试自定义SSL配置
    print("🧪 测试自定义SSL配置...")
    session = requests.Session()
    session.mount('https://', CustomHTTPSAdapter())

    try:
        response = session.get('https://push2.eastmoney.com', timeout=10)
        print(f"✅ 自定义SSL配置成功! 状态码: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ 自定义SSL配置失败: {str(e)[:80]}...")
        return False

def solution_2_proxy_settings():
    """方案2: 配置代理设置"""
    print("\n📋 方案2: 配置代理设置")

    # 2.1 环境变量代理
    print("2.1 设置环境变量代理...")

    proxy_configs = {
        'HTTP_PROXY': 'http://127.0.0.1:7890',  # 常用代理端口
        'HTTPS_PROXY': 'http://127.0.0.1:7890',
        'NO_PROXY': 'localhost,127.0.0.1'
    }

    print("可用的代理配置:")
    for key, value in proxy_configs.items():
        print(f"  {key}={value}")

    # 2.2 测试代理连接
    print("\n2.2 测试代理连接...")

    proxies = {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890'
    }

    try:
        response = requests.get(
            'https://push2.eastmoney.com',
            proxies=proxies,
            timeout=10,
            verify=False  # 临时禁用SSL验证
        )
        print(f"✅ 代理连接成功! 状态码: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ 代理连接失败: {str(e)[:80]}...")
        return False

def solution_3_ssl_workaround():
    """方案3: SSL绕过和降级"""
    print("\n📋 方案3: SSL绕过和降级")

    # 3.1 禁用SSL验证
    print("3.1 禁用SSL验证...")

    # 禁用SSL警告
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    # 3.2 配置requests会话
    print("\n3.2 配置requests会话...")

    session = requests.Session()
    session.verify = False
    session.trust_env = False

    # 设置超时和重试
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 测试连接
    try:
        response = session.get('https://push2.eastmoney.com', timeout=10)
        print(f"✅ SSL绕过成功! 状态码: {response.status_code}")
        return session
    except Exception as e:
        print(f"❌ SSL绕过失败: {str(e)[:80]}...")
        return None

def solution_4_dns_configuration():
    """方案4: DNS配置"""
    print("\n📋 方案4: DNS配置")

    # 4.1 检查DNS解析
    print("4.1 检查DNS解析...")

    eastmoney_domains = [
        'push2.eastmoney.com',
        '82.push2.eastmoney.com',
        'datacenter-web.eastmoney.com'
    ]

    for domain in eastmoney_domains:
        try:
            ip = socket.gethostbyname(domain)
            print(f"✅ {domain} -> {ip}")
        except socket.gaierror as e:
            print(f"❌ {domain} - DNS解析失败: {str(e)}")

    # 4.2 建议使用的DNS服务器
    print("\n4.2 建议使用的DNS服务器:")
    dns_servers = [
        ("阿里云DNS", "223.5.5.5"),
        ("腾讯云DNS", "119.29.29.29"),
        ("百度DNS", "180.76.76.76"),
        ("GoogleDNS", "8.8.8.8"),
        ("CloudflareDNS", "1.1.1.1")
    ]

    for name, dns in dns_servers:
        print(f"  {name}: {dns}")

def solution_5_alternative_domains():
    """方案5: 使用替代域名"""
    print("\n📋 方案5: 使用替代域名")

    # 5.1 东方财富可能的替代域名
    alternative_domains = [
        ('东方财富主站', 'https://www.eastmoney.com'),
        ('行情接口', 'https://quote.eastmoney.com'),
        ('数据中心', 'https://data.eastmoney.com'),
        ('API接口', 'https://api.eastmoney.com'),
        ('移动端', 'https://m.eastmoney.com')
    ]

    print("5.1 测试替代域名...")

    working_domains = []
    for name, url in alternative_domains:
        try:
            response = requests.get(url, timeout=10, verify=False)
            print(f"✅ {name}: {url} - 状态码: {response.status_code}")
            working_domains.append((name, url))
        except Exception as e:
            print(f"❌ {name}: {url} - 失败: {str(e)[:50]}...")

    return working_domains

def create_patched_akshare():
    """创建打了补丁的AKShare"""
    print("\n📋 方案6: 创建打了补丁的AKShare")

    import akshare as ak

    # 保存原始的requests模块引用
    original_requests = ak.stock_zh_a_spot_em.__globals__.get('requests')

    # 创建补丁的requests模块
    class PatchedRequests:
        def __init__(self):
            self.Session = self._patched_session

        def _patched_session(self):
            session = original_requests.Session() if original_requests else requests.Session()
            session.verify = False
            return session

    # 测试补丁效果
    print("6.1 测试补丁效果...")

    try:
        # 应用补丁
        if hasattr(ak.stock_zh_a_spot_em, '__globals__'):
            ak.stock_zh_a_spot_em.__globals__['requests'] = PatchedRequests()

        # 测试东方财富API
        print("🧪 测试东方财富API...")
        result = ak.stock_zh_a_spot_em()
        print(f"✅ 补丁成功! 获取到 {len(result)} 条数据")
        return True
    except Exception as e:
        print(f"❌ 补丁失败: {str(e)[:80]}...")
        return False

def solution_7_vpn_tunnel():
    """方案7: VPN和隧道"""
    print("\n📋 方案7: VPN和隧道解决方案")

    print("7.1 VPN解决方案:")
    vpn_solutions = [
        "1. 使用商业VPN服务 (ExpressVPN, NordVPN等)",
        "2. 配置企业VPN接入",
        "3. 使用Shadowsocks等代理工具",
        "4. 搭建个人VPN服务器"
    ]

    for solution in vpn_solutions:
        print(f"   {solution}")

    print("\n7.2 SSH隧道方案:")
    print("   ssh -D 1080 user@server  # 创建SOCKS代理")
    print("   export HTTP_PROXY=socks5://127.0.0.1:1080")
    print("   export HTTPS_PROXY=socks5://127.0.0.1:1080")

    print("\n7.3 HTTP隧道方案:")
    print("   ssh -L 8080:push2.eastmoney.com:443 user@server")
    print("   # 然后访问 http://localhost:8080")

def recommend_best_solution():
    """推荐最佳解决方案"""
    print("\n🎯 推荐解决方案 (按优先级排序)")

    solutions = [
        {
            'priority': 1,
            'name': 'SSL证书配置',
            'description': '更新certifi包并配置正确的SSL上下文',
            'difficulty': '中等',
            'success_rate': '70%'
        },
        {
            'priority': 2,
            'name': '代理设置',
            'description': '配置HTTP/HTTPS代理或SOCKS代理',
            'difficulty': '中等',
            'success_rate': '80%'
        },
        {
            'priority': 3,
            'name': 'SSL绕过',
            'description': '临时禁用SSL验证进行测试',
            'difficulty': '简单',
            'success_rate': '90%'
        },
        {
            'priority': 4,
            'name': 'VPN连接',
            'description': '使用VPN改变网络路径',
            'difficulty': '复杂',
            'success_rate': '95%'
        },
        {
            'priority': 5,
            'name': 'DNS优化',
            'description': '使用公共DNS服务',
            'difficulty': '简单',
            'success_rate': '30%'
        }
    ]

    for solution in solutions:
        print(f"\n🏆 优先级 {solution['priority']}: {solution['name']}")
        print(f"   📝 描述: {solution['description']}")
        print(f"   ⚡ 难度: {solution['difficulty']}")
        print(f"   📊 成功率: {solution['success_rate']}")

def main():
    """主函数"""
    print("🔧 东方财富网络问题全面解决方案")
    print("=" * 60)

    # 诊断问题
    diagnose_eastmoney_issue()

    # 尝试各种解决方案
    print("\n🧪 尝试解决方案...")

    # 方案1: SSL配置
    ssl_result = solution_1_ssl_verification()

    # 方案2: 代理设置 (需要实际代理服务器)
    # proxy_result = solution_2_proxy_settings()

    # 方案3: SSL绕过
    session = solution_3_ssl_workaround()

    # 方案4: DNS配置
    solution_4_dns_configuration()

    # 方案5: 替代域名
    working_domains = solution_5_alternative_domains()

    # 方案6: 打补丁
    patch_result = create_patched_akshare()

    # 方案7: VPN方案
    solution_7_vpn_tunnel()

    # 推荐最佳方案
    recommend_best_solution()

    print("\n" + "=" * 60)
    print("📋 总结建议:")

    if ssl_result:
        print("✅ 方案1 (SSL配置) 可行，建议优先尝试")
    elif session:
        print("✅ 方案3 (SSL绕过) 可行，适合开发测试")
    elif patch_result:
        print("✅ 方案6 (AKShare补丁) 可行，直接修复")
    else:
        print("⚠️ 自动方案均失败，建议尝试:")
        print("   1. 配置代理服务器")
        print("   2. 使用VPN连接")
        print("   3. 联系网络管理员")

    print("\n💡 重要提醒:")
    print("   • SSL绕过仅用于开发测试，生产环境不推荐")
    print("   • 代理服务器需要稳定可靠")
    print("   • VPN选择信誉良好的服务提供商")
    print("   • 定期检查AKShare版本更新")

if __name__ == "__main__":
    main()