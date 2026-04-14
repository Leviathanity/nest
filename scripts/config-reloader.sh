#!/bin/bash
#==============================================================================
# OpenClaw Cluster - Configuration Hot Reload Script
# 监听配置文件变化，自动重载 OpenClaw
#==============================================================================

set -e

INSTANCE_NAME=${INSTANCE_NAME:-openclaw}
CONFIG_BASE="/app/configs/base"
CONFIG_INSTANCE="/app/configs/instance"
OPENCLAW_DATA="/root/.openclaw"
OPENCLAW_CONFIG="$OPENCLAW_DATA/openclaw.json"

echo "[$INSTANCE_NAME] 启动配置热重载服务..."

setup_directories() {
    mkdir -p "$OPENCLAW_DATA/extensions"
    mkdir -p "$OPENCLAW_DATA/skills"
    mkdir -p "$OPENCLAW_DATA/browser/chrome/user-data"
    mkdir -p "$OPENCLAW_DATA/credentials"
    mkdir -p "$OPENCLAW_DATA/identity"
    mkdir -p "$OPENCLAW_DATA/logs"
}

merge_json_configs() {
    local base_json="$CONFIG_BASE/openclaw.json"
    local instance_json="$CONFIG_INSTANCE/openclaw.json"
    local output_json="$OPENCLAW_CONFIG"
    
    if [ -f "$base_json" ]; then
        if [ -f "$instance_json" ]; then
            python3 /usr/local/bin/merge_json.py "$base_json" "$instance_json" "$output_json"
        else
            cp "$base_json" "$output_json"
        fi
        echo "[$INSTANCE_NAME] JSON配置已合并"
    fi
}

copy_skills() {
    if [ -d "$CONFIG_BASE/skills" ]; then
        cp -rn "$CONFIG_BASE/skills/"* "$OPENCLAW_DATA/skills/" 2>/dev/null || true
    fi
    if [ -d "$CONFIG_INSTANCE/skills" ]; then
        cp -rn "$CONFIG_INSTANCE/skills/"* "$OPENCLAW_DATA/skills/" 2>/dev/null || true
    fi
    echo "[$INSTANCE_NAME] Skills配置已复制"
}

copy_plugins() {
    if [ -d "$CONFIG_BASE/plugins" ]; then
        cp -rn "$CONFIG_BASE/plugins/"* "$OPENCLAW_DATA/extensions/" 2>/dev/null || true
    fi
    if [ -d "$CONFIG_INSTANCE/plugins" ]; then
        cp -rn "$CONFIG_INSTANCE/plugins/"* "$OPENCLAW_DATA/extensions/" 2>/dev/null || true
    fi
    echo "[$INSTANCE_NAME] Plugins配置已复制"
}

merge_config() {
    echo "[$INSTANCE_NAME] 合并配置..."
    setup_directories
    merge_json_configs
    copy_skills
    copy_plugins
    echo "[$INSTANCE_NAME] 配置合并完成"
}

reload_openclaw() {
    echo "[$INSTANCE_NAME] 通知 OpenClaw 重载配置..."
    pkill -HUP -f "node.*openclaw.mjs" 2>/dev/null || true
}

start_openclaw() {
    echo "[$INSTANCE_NAME] 启动 OpenClaw..."
    cd /app
    exec node /app/openclaw.mjs gateway --bind 0.0.0.0 --port 18789 --allow-unconfigured
}

initial_config() {
    merge_config
    
    if [ -d "$CONFIG_BASE/skills" ]; then
        for skill_dir in "$CONFIG_BASE/skills"/*/; do
            if [ -d "$skill_dir" ]; then
                skill_name=$(basename "$skill_dir")
                mkdir -p "$OPENCLAW_DATA/skills/$skill_name"
                cp -r "$skill_dir"/* "$OPENCLAW_DATA/skills/$skill_name/" 2>/dev/null || true
            fi
        done
    fi
}

watch_config() {
    inotifywait -m -e modify,create,delete,move "$CONFIG_BASE" "$CONFIG_INSTANCE" 2>/dev/null &
    INOTIFY_PID=$!
    
    trap "kill $INOTIFY_PID 2>/dev/null; exit 0" SIGTERM SIGINT
    
    while read -r path action file; do
        echo "[$INSTANCE_NAME] 检测到配置变化: $path $action $file"
        merge_config
        reload_openclaw
    done &
}

initial_config
watch_config
start_openclaw
