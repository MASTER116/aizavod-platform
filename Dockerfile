FROM python:3.12-slim

WORKDIR /app

# System dependencies (including Playwright/Chromium deps + git + nodejs for claude)
RUN apt-get update && apt-get install -y --no-install-recommends     ffmpeg gcc git curl     libpq-dev fonts-dejavu-core     libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0     libcups2 libdrm2 libxkbcommon0 libxcomposite1     libxdamage1 libxfixes3 libxrandr2 libgbm1     libpango-1.0-0 libcairo2 libasound2     && rm -rf /var/lib/apt/lists/*

# Install Node.js for Claude Code CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -     && apt-get install -y nodejs     && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Application code
COPY . .

# Create directories
RUN mkdir -p media/reference media/generated media/processed logs hackathon_projects

EXPOSE 8000
CMD [uvicorn, backend.main:app, --host, 0.0.0.0, --port, 8000]
