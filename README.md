<p align="center">
  <img src="static/icon-512.png" width="120" alt="chatweb.ai logo">
</p>

<h1 align="center">chatweb.ai</h1>

<p align="center">
  <strong>Execute. Learn. Evolve. — Your AI Team.</strong><br>
  <em>39 agents × 12 models × A2A v1.0 — Open Source</em>
</p>

<p align="center">
  <a href="https://chatweb.ai">Live Demo</a> ·
  <a href="#features">Features</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#self-hosting">Self-Hosting</a> ·
  <a href="#api">API</a> ·
  <a href="#日本語">日本語</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Claude-Anthropic-6B46C1?logo=anthropic&logoColor=white" alt="Claude">
  <img src="https://img.shields.io/badge/deploy-Fly.io-8B5CF6?logo=fly.io&logoColor=white" alt="Fly.io">
  <img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="License">
  <img src="https://img.shields.io/badge/A2A-v1.0-8B5CF6" alt="A2A v1.0">
  <img src="https://img.shields.io/badge/agents-39-10b981" alt="39 Agents">
</p>

---

## What is chatweb.ai?

chatweb.ai is a **multi-agent AI platform** where 30+ specialized AI agents autonomously collaborate to complete complex tasks — from research and coding to email sending, deployment, and financial analysis.

Unlike traditional AI chatbots that just answer questions, chatweb.ai **executes**: it browses the web, writes code, sends emails, deploys apps, manages reservations, and more.

## Features

### 🧩 Custom Agent Creation
Build your own AI agents with custom system prompts. Fork built-in agents, customize their behavior, and share them with your team.

### ⚡ Multi-Agent Orchestration (A2A)
A single request can trigger multiple agents working in sequence. Example: *"Research competitors → analyze data → create slides → email the report"* — 4 agents collaborate automatically.

### 🔌 Real Tool Execution
Not simulated — agents actually execute tools:
- **Web Search**: Tavily, Perplexity, Wikipedia, DuckDuckGo
- **Browser Automation**: Playwright (screenshots, testing, scraping)
- **Email**: Gmail (read, send, draft)
- **Calendar**: Google Calendar (create, list events)
- **Code Execution**: E2B sandboxed code interpreter
- **File Analysis**: PDF, Excel, CSV parsing
- **Image Generation**: DALL-E
- **Deployment**: Fly.io deploy, Git operations
- **Reservations**: Beds24 property management
- **Notifications**: Slack, LINE, Telegram

### 🧠 Long-Term Memory
Automatically extracts and stores important information from conversations. Remembers user preferences, context, and history across sessions.

### 🌐 Instant Website Publishing
Generate HTML and publish it instantly at `yourname.chatweb.ai`. Portfolio sites, landing pages, event pages — created and hosted in seconds.

### 📱 LINE / Telegram Integration
Connect your LINE or Telegram account to access all agents from your favorite messenger.

### 🔒 Encrypted Secrets
API keys and tokens stored with Fernet encryption (AES-128-CBC + HMAC). Share secrets between users securely.

### 🔧 Self-Healing System
Automated feedback loop analyzes error logs, user ratings, and routing confidence every 6 hours. Identifies underperforming agents and suggests improvements.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    chatweb.ai                            │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Semantic  │→│ Agent    │→│ Tool     │              │
│  │ Router   │  │ Executor │  │ Runner   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│       ↓              ↓             ↓                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Planner  │  │ Memory   │  │ Feedback │              │
│  │ (A2A)    │  │ System   │  │ Loop     │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
│  Models: Qwen3-32B (Groq) │ Claude Sonnet │ Haiku      │
│  DB: SQLite (WAL) │ Encrypted Secrets │ Auto Backup    │
└─────────────────────────────────────────────────────────┘
         │              │              │
    Fly.io (nrt)    Cloudflare     LINE/Telegram
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 / FastAPI / Uvicorn |
| AI Models | Claude (Anthropic), Qwen3-32B (Groq), Gemini |
| Database | SQLite (WAL mode) + Fernet encryption |
| Browser | Playwright (Chromium) |
| Frontend | Vanilla HTML/CSS/JS (single-file, no build step) |
| Deploy | Fly.io (Tokyo nrt region) |
| CI/CD | GitHub Actions (test → staging → production) |
| Payments | Stripe (subscription billing) |
| Messaging | LINE Bot, Telegram Bot |

## Self-Hosting

### Docker (Recommended)

```bash
git clone https://github.com/yukihamada/chatweb.ai.git
cd chatweb.ai

# Set required env vars
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

docker build -t chatweb-ai .
docker run -p 8080:8080 -v chatweb_data:/data --env-file .env chatweb-ai
```

### Manual

```bash
pip install -r requirements.txt
playwright install chromium

# Required
export ANTHROPIC_API_KEY=sk-ant-...

# Optional (enables additional features)
export GROQ_API_KEY=gsk_...
export GOOGLE_CLIENT_ID=...
export GOOGLE_CLIENT_SECRET=...
export STRIPE_SECRET_KEY=sk_live_...

uvicorn main:app --host 0.0.0.0 --port 8080
```

### Fly.io

```bash
fly launch --name my-chatweb --region nrt
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

## API

### Chat (Streaming SSE)

```bash
POST /chat/stream/{session_id}
Content-Type: application/json

{"message": "Search for the latest AI news", "agent_id": "research"}
```

### External API

```bash
POST /api/v1/chat
X-API-Key: your-api-key
Content-Type: application/json

{"message": "Analyze NVDA stock", "agent_id": "finance"}
```

### Agent Management

```bash
# List all agents (with system prompts)
GET /agents

# Fork a built-in agent
POST /agents/{agent_id}/fork
{"name": "My Research Bot", "system_prompt": "You are..."}

# Create custom agent
POST /agents/custom
{"name": "Support Bot", "system_prompt": "...", "emoji": "🤖"}
```

### Admin

```bash
# System settings
GET /admin/settings
PUT /admin/settings/{key} {"value": "..."}

# Feedback analytics
GET /admin/feedback-report?hours=24

# Database backup
GET /admin/backup?token=...
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `GROQ_API_KEY` | No | Groq API key (Qwen3 economy tier) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth (login + Workspace) |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth secret |
| `STRIPE_SECRET_KEY` | No | Stripe payments |
| `STRIPE_WEBHOOK_SECRET` | No | Stripe webhook verification |
| `LINE_CHANNEL_ACCESS_TOKEN` | No | LINE Bot |
| `TELEGRAM_TOKEN` | No | Telegram Bot |
| `TAVILY_API_KEY` | No | Tavily search |
| `RESEND_API_KEY` | No | Email sending |
| `ADMIN_EMAILS` | No | Comma-separated admin emails |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<h2 id="日本語">🇯🇵 日本語</h2>

## chatweb.ai とは？

chatweb.aiは、**30以上の専門AIエージェントが自律的に連携する**マルチエージェントAIプラットフォームです。

従来のAIチャットのように「答えるだけ」ではなく、**実際に実行**します — Web検索、コード実行、メール送信、デプロイ、予約管理まで。

### 主な機能

| 機能 | 説明 |
|------|------|
| 🧩 カスタムエージェント | 自分専用のAIエージェントを作成・フォーク・共有 |
| ⚡ マルチエージェント連携 | 複数エージェントが自動で協力してタスク完了 |
| 🔌 実ツール実行 | Gmail送信、カレンダー登録、Playwright操作、コード実行 |
| 🧠 長期記憶 | 会話から重要情報を自動記憶、次回以降に活用 |
| 🌐 サイト公開 | HTMLを生成して yourname.chatweb.ai で即公開 |
| 📱 LINE/Telegram連携 | メッセンジャーからエージェントにアクセス |
| 🔒 暗号化シークレット | APIキーをFernet暗号化で安全に保存・共有 |
| 🔧 自動改善 | フィードバックループで6時間ごとに自動分析・改善提案 |

### モデル構成

| ティア | モデル | 用途 |
|--------|--------|------|
| エコノミー（デフォルト） | Qwen3-32B (Groq) | 一般的な質問・タスク |
| プロ | Claude Sonnet 4.6 | 高品質な推論・分析 |
| 金融/法務 | Claude Sonnet（常時） | 専門性が必要な領域 |

### セルフホスト

```bash
git clone https://github.com/yukihamada/chatweb.ai.git
cd chatweb.ai
export ANTHROPIC_API_KEY=sk-ant-...
docker build -t chatweb-ai . && docker run -p 8080:8080 -v data:/data --env-file .env chatweb-ai
```

### 関連プロダクト

- **[Elio](https://elio.love)** — オフラインで動作するP2P分散型AIチャット（iOS）

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/yukihamada">@yukihamada</a>
</p>
