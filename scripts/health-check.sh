#!/bin/bash
#==============================================================================
# OpenClaw Cluster - Health Check Script
#==============================================================================

INSTANCE_NAME=${INSTANCE_NAME:-openclaw}
GATEWAY_URL=${GATEWAY_URL:-http://localhost:18789}

check_gateway() {
    if curl -sf "$GATEWAY_URL/health" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

check_process() {
    if pgrep -f "node.*openclaw.mjs" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

if check_gateway; then
    echo "[$INSTANCE_NAME] Health: OK"
    exit 0
elif check_process; then
    echo "[$INSTANCE_NAME] Health: DEGRADED (gateway not responding)"
    exit 1
else
    echo "[$INSTANCE_NAME] Health: FAILED"
    exit 2
fi
