#!/bin/bash
# GOST MySQL Tunnel Health Check Script
# EPIC-011 Story 11.2: SSH 隧道自动重连
# 
# 功能:
# 1. 每 10s 检测隧道连通性
# 2. 记录重连事件到 Prometheus Pushgateway
# 3. 隧道断开时触发告警

set -euo pipefail

# ========== 配置 ==========
TUNNEL_LOCAL_PORT=36301
TUNNEL_REMOTE_HOST="43.145.51.23"
TUNNEL_REMOTE_PORT=26300
CHECK_INTERVAL=10
MAX_RETRY=3
PROMETHEUS_PUSHGATEWAY="http://127.0.0.1:9091"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"

# ========== 日志函数 ==========
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/gost_health_check.log
}

# ========== 检测隧道连通性 ==========
check_tunnel() {
    # 尝试通过隧道连接远程 MySQL
    timeout 5 bash -c "echo > /dev/tcp/127.0.0.1/${TUNNEL_LOCAL_PORT}" 2>/dev/null
    return $?
}

# ========== 上报 Prometheus 指标 ==========
push_metric() {
    local metric_name=$1
    local metric_value=$2
    local metric_help=$3
    
    if [[ -z "$PROMETHEUS_PUSHGATEWAY" ]]; then
        return 0
    fi
    
    cat <<EOF | curl --data-binary @- "${PROMETHEUS_PUSHGATEWAY}/metrics/job/gost_tunnel/instance/server41" 2>/dev/null || true
# HELP ${metric_name} ${metric_help}
# TYPE ${metric_name} counter
${metric_name} ${metric_value}
EOF
}

# ========== 发送告警 ==========
send_alert() {
    local message=$1
    
    log "ALERT: $message"
    
    if [[ -n "$ALERT_WEBHOOK_URL" ]]; then
        curl -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"[GOST Tunnel] $message\", \"level\": \"error\"}" \
            2>/dev/null || true
    fi
}

# ========== 主循环 ==========
main() {
    log "GOST Tunnel Health Check started (interval: ${CHECK_INTERVAL}s)"
    
    local consecutive_failures=0
    local total_checks=0
    local total_failures=0
    
    while true; do
        total_checks=$((total_checks + 1))
        
        if check_tunnel; then
            if [[ $consecutive_failures -gt 0 ]]; then
                log "Tunnel recovered after ${consecutive_failures} failures"
                push_metric "gost_tunnel_reconnect_total" 1 "Total number of tunnel reconnections"
                consecutive_failures=0
            fi
            
            # 上报健康状态
            push_metric "gost_tunnel_health" 1 "Tunnel health status (1=healthy, 0=unhealthy)"
        else
            consecutive_failures=$((consecutive_failures + 1))
            total_failures=$((total_failures + 1))
            
            log "Tunnel check failed (${consecutive_failures}/${MAX_RETRY})"
            
            # 上报不健康状态
            push_metric "gost_tunnel_health" 0 "Tunnel health status (1=healthy, 0=unhealthy)"
            
            # 连续失败超过阈值时触发告警
            if [[ $consecutive_failures -ge $MAX_RETRY ]]; then
                send_alert "Tunnel down for ${consecutive_failures} consecutive checks (${consecutive_failures}0s)"
            fi
        fi
        
        # 每 100 次检查上报统计信息
        if [[ $((total_checks % 100)) -eq 0 ]]; then
            log "Stats: total_checks=${total_checks}, total_failures=${total_failures}, success_rate=$((100 * (total_checks - total_failures) / total_checks))%"
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# ========== 启动 ==========
main
