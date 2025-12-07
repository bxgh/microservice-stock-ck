#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富网络问题快速修复脚本
提供一键解决方案
"""

import os
import sys
import subprocess
import ssl
import urllib3
import requests
import akshare as ak

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f" {title} ")
    print(f"{'='*60}")

def fix_option_1_ssl_bypass():
    """选项1: SSL绕过 (快速测试)"""
    print_header("选项1: SSL绕过 (开发测试用)")

    try:
        # 禁用SSL警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # 创建不验证SSL的上下文
        ssl._create_default_https_context = ssl._create_unverified_context

        print("✅ SSL绕过已启用")
        print("⚠️  仅用于开发测试，生产环境不推荐")

        # 测试连接
        print("🧪 测试东方财富连接...")
        result = ak.stock_zh_a_spot_em()
        print(f"✅ 成功! 获取到 {len(result)} 条股票数据")
        print("📊 前5条数据:")
        print(result.head())
        return True

    except Exception as e:
        print(f"❌ SSL绕过失败: {str(e)[:100]}...")
        return False

def fix_option_2_proxy():
    """选项2: 配置代理"""
    print_header("选项2: 配置代理设置")

    # 常用代理端口
    proxy_configs = [
        "http://127.0.0.1:7890",  # Clash默认端口
        "http://127.0.0.1:1080",  # Shadowsocks默认端口
        "http://127.0.0.1:8080",  # 通用代理端口
        "socks5://127.0.0.1:1080",  # SOCKS5代理
    ]

    print("🌐 配置代理环境变量...")

    for i, proxy in enumerate(proxy_configs, 1):
        print(f"\n尝试代理配置 {i}: {proxy}")

        # 设置环境变量
        os.environ['HTTP_PROXY'] = proxy
        os.environ['HTTPS_PROXY'] = proxy

        try:
            print("🧪 测试代理连接...")

            # 简单的HTTP测试
            import requests
            session = requests.Session()
            session.proxies = {
                'http': proxy,
                'https': proxy
            }
            session.verify = False

            # 测试东方财富
            response = session.get('https://push2.eastmoney.com', timeout=5)
            print(f"✅ 代理 {proxy} 连接成功! 状态码: {response.status_code}")

            # 测试AKShare
            result = ak.stock_zh_a_spot_em()
            print(f"✅ 通过代理成功获取数据: {len(result)} 条")
            return True

        except Exception as e:
            print(f"❌ 代理 {proxy} 失败: {str(e)[:50]}...")
            continue

    print("\n❌ 所有代理配置均失败")
    print("💡 建议:")
    print("   1. 检查代理服务器是否正在运行")
    print("   2. 确认代理端口配置正确")
    print("   3. 尝试其他代理端口")
    return False

def fix_option_3_install_tools():
    """选项3: 安装代理工具"""
    print_header("选项3: 安装和配置代理工具")

    print("🔧 安装代理工具...")

    tools = [
        {
            'name': 'requests[socks]',
            'purpose': 'SOCKS代理支持',
            'command': [sys.executable, '-m', 'pip', 'install', 'requests[socks]']
        },
        {
            'name': 'pysocks',
            'purpose': 'Python SOCKS支持',
            'command': [sys.executable, '-m', 'pip', 'install', 'pysocks']
        },
        {
            'name': 'certifi',
            'purpose': '更新SSL证书',
            'command': [sys.executable, '-m', 'pip', 'install', '--upgrade', 'certifi']
        }
    ]

    for tool in tools:
        try:
            print(f"📦 安装 {tool['name']} ({tool['purpose']})...")
            subprocess.check_call(tool['command'], capture_output=True)
            print(f"✅ {tool['name']} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ {tool['name']} 安装失败: {e}")
        except Exception as e:
            print(f"❌ {tool['name']} 安装异常: {e}")

    print("\n💡 代理工具配置说明:")
    print("1. Clash: https://github.com/Dreamacro/clash")
    print("2. V2Ray: https://github.com/v2fly/v2ray-core")
    print("3. Shadowsocks: https://github.com/shadowsocks/shadowsocks-rust")

def fix_option_4_dns_config():
    """选项4: DNS配置"""
    print_header("选项4: DNS配置")

    print("🌐 建议使用的DNS服务器:")
    dns_servers = [
        ("阿里云DNS", "223.5.5.5", "223.6.6.6"),
        ("腾讯云DNS", "119.29.29.29", "182.254.116.116"),
        ("百度DNS", "180.76.76.76", "180.76.76.75"),
        ("GoogleDNS", "8.8.8.8", "8.8.4.4"),
        ("CloudflareDNS", "1.1.1.1", "1.0.0.1")
    ]

    for name, primary, secondary in dns_servers:
        print(f"  {name}: {primary}, {secondary}")

    print("\n🔧 配置DNS的方法:")
    print("1. 临时配置:")
    print("   sudo echo 'nameserver 223.5.5.5' > /etc/resolv.conf")
    print("\n2. 永久配置:")
    print("   sudo nano /etc/netplan/01-netcfg.yaml")
    print("   # 添加DNS配置并重启网络服务")
    print("\n3. NetworkManager:")
    print("   nmcli connection modify eth0 ipv4.dns 223.5.5.5,223.6.6.6")

def fix_option_5_vpn_info():
    """选项5: VPN信息"""
    print_header("选项5: VPN解决方案")

    print("🏆 推荐VPN服务:")
    vpn_services = [
        {
            'name': 'ExpressVPN',
            'features': '速度快，稳定性好，中国优化服务器',
            'difficulty': '⭐⭐',
            'price': '付费'
        },
        {
            'name': 'NordVPN',
            'features': '安全性高，服务器众多，无日志政策',
            'difficulty': '⭐⭐',
            'price': '付费'
        },
        {
            'name': '阿里云VPN',
            'features': '国内企业解决方案，技术支持好',
            'difficulty': '⭐⭐⭐',
            'price': '付费'
        }
    ]

    for vpn in vpn_services:
        print(f"\n  🏷️  {vpn['name']}")
        print(f"     特点: {vpn['features']}")
        print(f"     难度: {vpn['difficulty']}")
        print(f"     价格: {vpn['price']}")

    print("\n🆓 开源VPN方案:")
    print("1. Shadowsocks (ss)")
    print("2. V2Ray (vmess/vless)")
    print("3. Xray-core")
    print("4. Trojan")

def interactive_menu():
    """交互式菜单"""
    print_header("东方财富网络问题修复工具")
    print("请选择修复方案:")

    options = [
        "1. SSL绕过 (开发测试用 - 最简单)",
        "2. 配置代理 (需要代理服务器 - 中等)",
        "3. 安装代理工具 (需要后续配置 - 复杂)",
        "4. DNS配置 (网络优化 - 简单)",
        "5. VPN信息 (需要VPN服务 - 复杂)",
        "6. 运行所有诊断 (推荐新手)",
        "0. 退出"
    ]

    for option in options:
        print(f"  {option}")

    while True:
        try:
            choice = input("\n请输入选项 (0-6): ").strip()

            if choice == '1':
                fix_option_1_ssl_bypass()
                break
            elif choice == '2':
                fix_option_2_proxy()
                break
            elif choice == '3':
                fix_option_3_install_tools()
                break
            elif choice == '4':
                fix_option_4_dns_config()
                break
            elif choice == '5':
                fix_option_5_vpn_info()
                break
            elif choice == '6':
                run_all_diagnostics()
                break
            elif choice == '0':
                print("👋 退出程序")
                return
            else:
                print("❌ 无效选项，请重新输入")
        except KeyboardInterrupt:
            print("\n👋 用户中断，退出程序")
            return

def run_all_diagnostics():
    """运行所有诊断"""
    print_header("运行所有诊断和修复尝试")

    # 1. SSL绕过测试
    print("\n🔄 1/4 尝试SSL绕过...")
    ssl_success = fix_option_1_ssl_bypass()

    if not ssl_success:
        # 2. 代理测试
        print("\n🔄 2/4 尝试代理配置...")
        proxy_success = fix_option_2_proxy()

        if not proxy_success:
            # 3. 显示其他选项
            print("\n🔄 3/4 显示其他解决方案...")
            fix_option_3_install_tools()
            fix_option_4_dns_config()
            fix_option_5_vpn_info()

    print("\n" + "="*60)
    print("📋 诊断完成!")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 命令行参数模式
        arg = sys.argv[1]
        if arg == 'ssl':
            fix_option_1_ssl_bypass()
        elif arg == 'proxy':
            fix_option_2_proxy()
        elif arg == 'tools':
            fix_option_3_install_tools()
        elif arg == 'dns':
            fix_option_4_dns_config()
        elif arg == 'vpn':
            fix_option_5_vpn_info()
        elif arg == 'all':
            run_all_diagnostics()
        else:
            print("❌ 未知参数，使用交互模式")
            interactive_menu()
    else:
        # 交互模式
        interactive_menu()

if __name__ == "__main__":
    main()