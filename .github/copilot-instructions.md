# Trading-FAIT Copilot Instructions

## Project Overview

Trading-FAIT is a containerized AI-agent trading assistant using **Magentic-One (Microsoft AutoGen)** with **Azure OpenAI GPT-4o**. It provides trading analysis for stocks and crypto via natural language queries—**no order execution, only recommendations**.

## Architecture

```
Frontend (Next.js 14) ←WebSocket→ Backend (FastAPI) → MagenticOneGroupChat
                                                      ├── MarketAnalyst
                                                      ├── NewsResearcher (WebSurfer)
                                                      ├── ChartConfigurator
                                                      ├── ReportWriter
                                                      ├── IndicatorCoder
                                                      └── CodeExecutor
```

- **6 AI Agents** discuss with soft-criticism, terminate on 2/3 majority consensus
- **WebSocket streaming** for real-time agent status (Activity Dots in UI)
- **Agent discussions** logged to `/logs/discussions/` (JSON), NOT displayed in UI

## Key Directories

| Path | Purpose |
|------|---------|
| `backend/app/agents/` | Magentic-One agent team, prompts, termination logic |
| `backend/app/services/` | Market data (yfinance, ccxt), technical indicators |
| `backend/app/api/websocket.py` | WebSocket handler for frontend streaming |
| `frontend/components/` | React components: ActivityDots, TradeCard, TradingViewWidget |
| `Planning/` | Project roadmap, architecture docs, status tracking |

## Development Commands

```bash
# Backend (local dev)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

# Frontend (local dev)
cd frontend && npm install && npm run dev

# Full stack (Docker)
docker-compose up --build
```

## Code Patterns

### Backend (Python)
- Use **Pydantic v2** for all models and settings (`backend/app/core/config.py`)
- Use **structlog** for JSON logging to files, not stdout
- Agent system prompts in `backend/app/agents/prompts.py` use **soft-criticism** style
- Azure OpenAI client: `AzureOpenAIChatCompletionClient` from `autogen_ext.models.openai`

### Frontend (TypeScript)
- **Next.js 14 App Router** with `/app` directory structure
- Types defined in `frontend/lib/types.ts` (AgentStatus, TradeRecommendation, etc.)
- TradingView **Free Widgets only** (no Pro account)—no custom drawings
- Activity Dots: 6 subtle dots showing agent activity, pulse animation when active

### WebSocket Protocol
```typescript
// Client → Server
{ type: "query", message: "Analysiere BTC" }

// Server → Client
{ type: "agent_status", agent: "MarketAnalyst", active: true }
{ type: "trade_recommendation", data: { symbol, entry, stopLoss, takeProfit } }
{ type: "report", markdown: "# Analysis..." }
```

## Critical Constraints

- **No order execution**—only generate trade recommendations with Entry/SL/TP
- **max_turns=20** for agent discussions, **max_stalls=3** before re-planning
- **Majority consensus** (2/3 agents) terminates discussion
- **Asset-agnostic**: Support both `AAPL` (yfinance) and `BTC/USDT` (ccxt) formats
- Logs go to **files only** (`/logs/discussions/`), no database

## Status & Roadmap

Check `Planning/STATUS.md` for current implementation phase. Key phases:
1. ✅ Project structure
2. 🔴 Backend core (config, logging)
3. 🔴 Magentic-One agents
4. 🔴 Market data services
5. 🔴 WebSocket API
6-7. 🔴 Frontend components
8-9. 🔴 Docker integration & testing

## Environment Variables

Required in `.env` (copy from `.env.example`):
```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```
