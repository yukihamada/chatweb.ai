FROM python:3.12-slim

# System deps for Playwright/Chromium + git + gh CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl ca-certificates gnupg git \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    libx11-6 libxcb1 libxext6 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (gh)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && apt-get install -y gh && rm -rf /var/lib/apt/lists/*

# Install Fly CLI
RUN curl -L https://fly.io/install.sh | FLYCTL_INSTALL=/usr/local sh 2>/dev/null || \
    curl -L https://github.com/superfly/flyctl/releases/latest/download/flyctl_Linux_x86_64.tar.gz \
    | tar -xz -C /usr/local/bin flyctl && ln -sf /usr/local/bin/flyctl /usr/local/bin/fly

# Install gogcli (Google Workspace CLI) — https://gogcli.sh
RUN curl -fsSL https://gogcli.sh/install.sh | sh 2>/dev/null || \
    (echo "gogcli install via script failed, trying GitHub releases" && \
    GOGCLI_VERSION=$(curl -fsSL https://api.github.com/repos/steipete/gogcli/releases/latest | grep '"tag_name"' | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/') && \
    curl -fsSL "https://github.com/steipete/gogcli/releases/download/${GOGCLI_VERSION}/gogcli_Linux_x86_64.tar.gz" \
    | tar -xz -C /usr/local/bin 2>/dev/null) || echo "gogcli not available — Google Workspace agents will show setup instructions"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium browser for Playwright
RUN playwright install chromium

COPY . .

RUN mkdir -p static/screenshots /data

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
