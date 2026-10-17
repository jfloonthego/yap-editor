# The Yap worker in a container: runs anywhere Docker runs (Cloudflare Containers, Fly.io, Railway, Render, a VPS), so edits happen with your own computer off.
# It needs only two settings at run time: SOCIAL_STUDIO_URL and SOCIAL_STUDIO_TOKEN (from Social Studio -> Setup -> Connections -> Reel editor).
#   docker build -t yap-worker . && docker run --rm -e SOCIAL_STUDIO_URL=https://rei.jesemm.com -e SOCIAL_STUDIO_TOKEN=... yap-worker
FROM node:20-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 ffmpeg ca-certificates \
      chromium fonts-liberation libnss3 libatk-bridge2.0-0 libgbm1 libasound2 libxkbcommon0 libxdamage1 libxrandr2 libxcomposite1 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY render/package.json render/package-lock.json ./render/
RUN cd render && npm ci --no-audit --no-fund
COPY . .
ENV REMOTION_BROWSER=/usr/bin/chromium
CMD ["python3", "scripts/worker.py"]
