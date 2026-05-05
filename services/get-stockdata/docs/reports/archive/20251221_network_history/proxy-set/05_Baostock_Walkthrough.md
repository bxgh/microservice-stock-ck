# Baostock Login Debugging Walkthrough

## Issue
- **Error:** `10002007` Network Receive Error / Broken Pipe.
- **Cause:** Baostock connects to `www.baostock.com:10030`. The default Privoxy (port 8118) on the host blocked `CONNECT` requests to non-standard ports (like 10030), or Baostock ignored standard HTTP proxy environment variables for its custom protocol.

## Solution
We implemented a solution using **Proxychains** to force traffic through a SOCKS tunnel, chained to the more permissive Squid proxy.

### Network Path
`Container (Proxychains)` -> `Host Gost (:8900)` -> `Squid Proxy (192.168.151.18:3128)` -> `Internet`

### Steps Taken
1.  **Identified blocked traffic:** Confirmed local Privoxy (8118) restricted traffic.
2.  **Identified working upstream:** Verified `192.168.151.18:3128` (Squid) allows the connection.
3.  **Deployed Bridge Proxy:** Started a `gost` instance on the host (`192.168.151.41:8900`) to act as a SOCKS5 frontend for the Squid proxy.
    ```bash
    /usr/local/bin/gost -L :8900 -F http://192.168.151.18:3128
    ```
4.  **Configured Container:**
    -   Installed `proxychains4` (Debian Trixie).
    -   Configured `/etc/proxychains4.conf` to use `socks5 192.168.151.41 8900`.
5.  **Verified Login:**
    -   Ran `proxychains4 python ...`
    -   Result: `login success!`

## Recommendation for Persistence
To make this permanent:
1.  Ensure the `gost` instance on port 8900 is managed by systemd (e.g., update `gost-domestic.service` or create a new one).
2.  Add `proxychains4` installation to the container's Dockerfile.
