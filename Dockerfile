#==============================================================================
# OpenClaw Cluster - Base Image
#==============================================================================
#
# Build: docker build -t openclaw-cluster:latest .
# Run:   由 docker-compose.yml 调用
#
#==============================================================================

ARG GPU_BASE=

#==============================================================================
# Stage 1: Clone OpenClaw source code
#==============================================================================
FROM node:22-bookworm-slim AS clone

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/openclaw/openclaw.git /app && git checkout 6640b352988b903804eebd6548d12c41e5effd88

#==============================================================================
# Stage 2: Build OpenClaw (core + UI)
#==============================================================================
FROM node:22-bookworm-slim AS builder

RUN npm install -g pnpm
COPY --from=clone /app /app
RUN cd /app && pnpm install --frozen-lockfile && pnpm build && pnpm ui:build

#==============================================================================
# Stage 3: Final image with all dependencies
#==============================================================================
FROM ${GPU_BASE:-node:22-bookworm-slim} AS openclaw-cluster

#-----------------------------------------------------------------------------
# System dependencies (使用清华/阿里云源)
#-----------------------------------------------------------------------------
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
        wget \
        gnupg2 \
        ffmpeg \
        python3-pip \
        python3-venv \
        python3-yaml \
        android-tools-adb \
        inotify-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (使用镜像)
RUN curl -fsSL https://npmmirror.com/mirrors/nodev22.x/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists*

#-----------------------------------------------------------------------------
# Google Chrome for browser automation
#-----------------------------------------------------------------------------
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

#-----------------------------------------------------------------------------
# Python packages (使用清华/阿里云源)
#-----------------------------------------------------------------------------
RUN pip install --no-cache-dir --break-system-packages -i https://pypi.tuna.tsinghua.edu.cn/simple \
        playwright \
        faster-whisper \
        nvidia-cublas-cu12 \
        nvidia-cudnn-cu12

RUN python -m playwright install chromium --with-deps || true

#-----------------------------------------------------------------------------
# Copy built application
#-----------------------------------------------------------------------------
COPY --from=builder /app /app

#-----------------------------------------------------------------------------
# OpenClaw CLI installation
#-----------------------------------------------------------------------------
RUN mkdir -p /root && cd /app && npm install -g .

#-----------------------------------------------------------------------------
# Directory structure
#-----------------------------------------------------------------------------
RUN mkdir -p /root/.openclaw/extensions \
             /root/.openclaw/skills \
             /root/.openclaw/browser/chrome/user-data \
             /root/.openclaw/credentials \
             /root/.openclaw/identity \
             /root/.cache/huggingface/hub \
             /app/configs/base \
             /app/configs/instance

#-----------------------------------------------------------------------------
# Scripts
#-----------------------------------------------------------------------------
COPY scripts/config-reloader.sh /usr/local/bin/config-reloader.sh
COPY scripts/merge_json.py /usr/local/bin/merge_json.py

RUN chmod +x /usr/local/bin/config-reloader.sh \
             /usr/local/bin/merge_json.py

#-----------------------------------------------------------------------------
# Configuration
#-----------------------------------------------------------------------------
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# GPU environment variables
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Runtime configuration
USER root
WORKDIR /app

EXPOSE 18789 18790 5555

# 配置热重载入口
CMD ["/usr/local/bin/config-reloader.sh"]
