# ============================================
# Stage 1: Build rednote-mcp (Node.js)
# ============================================
FROM node:20-slim AS mcp-builder

WORKDIR /mcp
COPY rednote-mcp/package*.json ./
RUN npm ci

COPY rednote-mcp/ ./
RUN npm run build

# ============================================
# Stage 2: Build Frontend (Vue.js)
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY rednote_research/frontend/package*.json ./
RUN npm ci

COPY rednote_research/frontend/ ./
RUN npm run build

# ============================================
# Stage 3: Runtime (使用 Ubuntu 基础镜像)
# ============================================
FROM ubuntu:22.04

# 设置非交互模式
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 安装 Python、Node.js 和 Playwright 依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3-pip \
    curl \
    gnupg \
    # Playwright 依赖
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# 创建 python 软链接
RUN ln -sf /usr/bin/python3.11 /usr/bin/python

# Copy MCP server from builder
COPY --from=mcp-builder /mcp /app/rednote-mcp

# Install MCP dependencies and Playwright Chromium
WORKDIR /app/rednote-mcp
RUN npm ci --omit=dev \
    && npx playwright install chromium

# Install Python application
WORKDIR /app
COPY rednote_research/pyproject.toml ./rednote_research/
COPY rednote_research/__init__.py ./rednote_research/
COPY rednote_research/agents/ ./rednote_research/agents/
COPY rednote_research/mcp/ ./rednote_research/mcp/
COPY rednote_research/output/ ./rednote_research/output/
COPY rednote_research/prompts/ ./rednote_research/prompts/
COPY rednote_research/services/ ./rednote_research/services/
COPY rednote_research/web/ ./rednote_research/web/
COPY rednote_research/cli.py ./rednote_research/
COPY rednote_research/config.py ./rednote_research/
COPY rednote_research/state.py ./rednote_research/
# Install Python dependencies first (use python3.11 -m pip to ensure correct Python version)
RUN python3.11 -m pip install --no-cache-dir \
    "mcp>=1.0.0" \
    "openai>=1.0.0" \
    "pydantic>=2.0.0" \
    "jinja2>=3.0.0" \
    "rich>=13.0.0" \
    "fastapi>=0.100.0" \
    "sse-starlette>=1.0.0" \
    "uvicorn>=0.20.0" \
    "pyyaml>=6.0.0" \
    "python-dotenv>=1.0.0"

# Install Python application
RUN python3.11 -m pip install --no-cache-dir ./rednote_research

# Copy frontend build to static directory
COPY --from=frontend-builder /frontend/dist ./rednote_research/web/static

# Create reports directory
RUN mkdir -p /app/reports

# Copy entrypoint script and convert CRLF to LF (in case of Windows line endings)
COPY docker/entrypoint.sh ./
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Set environment
ENV REDNOTE_MCP_PATH=/app/rednote-mcp/dist/index.js
ENV PYTHONUNBUFFERED=1

# Run application
CMD ["./entrypoint.sh"]
