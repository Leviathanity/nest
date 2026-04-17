#!/bin/bash
# 和平精英/游戏新闻获取脚本
# 从游民星空获取最新游戏资讯

NEWS=$(curl -s "https://www.gamersky.com/news" | grep -oP '(?<=href=").*?gamersky\.com/news/\d{6}/\d+\.shtml' | head -1)
if [ -n "$NEWS" ]; then
    echo "🎮 游戏快报：最新资讯更新中..."
    echo "来源：游民星空 Gamersky"
    echo "时间：$(date '+%H:%M:%S')"
else
    echo "🎮 游戏快报"
    echo "暂无更新"
fi
