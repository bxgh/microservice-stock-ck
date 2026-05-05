import pymysql
import os

# Test direct connection via GOST tunnel
try:
    # Stop the systemd service first to free up port
    os.system("sudo systemctl stop gost-mysql-tunnel 2>/dev/null")
    
    # Launch manual GOST tunnel that bypasses iptables
    # This will forward directly WITHOUT going through iptables routing
    os.system("sudo /usr/local/bin/gost -L tcp://:36301/43.145.51.23:26300 -F http://127.0.0.1:8118 > /tmp/manual_tunnel.log 2>&1 &")
    
    import time
    time.sleep(2)
    
    conn = pymysql.connect(
        host='127.0.0.1',
        port=36301,
        user='root',
        password='alwaysup@888',
        database='alwaysup',
        connect_timeout=10
    )
    print("✅ SUCCESS: Connected via SSH tunnel (port 8118)")
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"MySQL Version: {version[0]}")
    conn.close()
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    
# Check tunnel log
print("\n=== Tunnel Log ===")
os.system("tail -20 /tmp/manual_tunnel.log")
