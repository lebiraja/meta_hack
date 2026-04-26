FROM python:3.11-slim

WORKDIR /app

# Install system deps: curl (healthcheck) + nginx + Node.js 22
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl nginx gnupg ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# ── Python deps ───────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# ── Frontend build ────────────────────────────────────────────────────────────
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm ci --prefer-offline

# NEXT_PUBLIC_API_URL="" → relative URLs → nginx routes them to FastAPI on 8080
ENV NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_KEY=meta_hack_2026
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ── Python source ─────────────────────────────────────────────────────────────
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -e .

# ── nginx config ──────────────────────────────────────────────────────────────
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
