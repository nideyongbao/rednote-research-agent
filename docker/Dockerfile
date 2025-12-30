# ============================================
# Stage 1: Build Frontend (Vue.js)
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY rednote_research/frontend/package*.json ./
RUN npm ci

COPY rednote_research/frontend/ ./
RUN npm run build

# ============================================
# Stage 2: Runtime (使用 Ubuntu 基础镜像)
# ============================================
FROM ubuntu:22.04

# 设置非交互模式
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 安装 Python (不再需要 Node.js 和 Playwright，因为 MCP 已分离)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建 python 软链接
RUN ln -sf /usr/bin/python3.11 /usr/bin/python

# Install Python dependencies first
# Copy pyproject.toml separately to leverage cache
WORKDIR /app
COPY rednote_research/pyproject.toml ./rednote_research/
# Install dependencies
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
    "python-dotenv>=1.0.0" \
    "httpx>=0.24.0" \
    "aiohttp>=3.9.0"

# Install Python application
COPY rednote_research/ ./rednote_research/
RUN python3.11 -m pip install --no-cache-dir ./rednote_research

# Copy frontend build to static directory
COPY --from=frontend-builder /frontend/dist ./rednote_research/web/static

# Create reports directory
RUN mkdir -p /app/reports /app/data /app/output

# Copy entrypoint script
COPY docker/entrypoint.sh ./
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Set environment
ENV PYTHONUNBUFFERED=1
ENV XIAOHONGSHU_MCP_URL=http://xiaohongshu-mcp:18060

# Run application
CMD ["./entrypoint.sh"]
