
import socket

def test_ip_interface(ip, bind_ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        if bind_ip:
            sock.bind((bind_ip, 0))
        sock.connect((ip, 7709))
        sock.close()
        return True
    except Exception as e:
        return str(e)

golden_ips = ["175.6.5.153", "139.9.51.18", "139.159.239.163"]
interfaces = [
    ("192.168.151.111", "ens32"),
    ("192.168.151.37", "ens35"),
    (None, "Default")
]

for ip in golden_ips:
    print(f"\nTarget: {ip}")
    for bind, name in interfaces:
        res = test_ip_interface(ip, bind)
        status = "✅" if res is True else f"❌ ({res})"
        print(f"  {name:10} ({bind or 'Any'}): {status}")
