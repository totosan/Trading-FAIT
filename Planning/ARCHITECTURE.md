# Trading-FAIT Architektur

> **Version:** 1.0 | **Letzte Aktualisierung:** 12.12.2024

---

## 🏗️ System-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Next.js 14 Frontend                                      │  │
│  │  ├── Chat-Interface (Fragen eingeben)                    │  │
│  │  ├── Activity Dots (6 Agenten-Status)                    │  │
│  │  ├── TradingView Free Widget (Live-Chart)                │  │
│  │  ├── Trade-Card (Entry/SL/TP)                            │  │
│  │  └── Markdown Report Viewer                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ WebSocket (ws://backend:8000/ws) │
│                              ▼                                   │
├─────────────────────────────────────────────────────────────────┤
│                      DOCKER NETWORK                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend (:8000)                                  │  │
│  │  ├── /ws/chat         → WebSocket Handler                │  │
│  │  ├── /api/quote/{sym} → Quick Quote (optional)           │  │
│  │  └── CORS für Frontend                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  MagenticOneGroupChat (Orchestrator)                      │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │ Market      │  │ News        │  │ Chart       │       │  │
│  │  │ Analyst     │◄─┤ Researcher  │◄─┤ Configurator│       │  │
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘       │  │
│  │         │                │                                │  │
│  │         ▼                ▼                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │ Indicator   │  │ Code        │  │ Report      │       │  │
│  │  │ Coder       │─►│ Executor    │  │ Writer      │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  │                                                           │  │
│  │  Termination: max_turns=20, Mehrheits-Konsens (2/3)      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │ Azure       │     │ yfinance    │     │ ccxt        │       │
│  │ OpenAI      │     │ (Aktien)    │     │ (Krypto)    │       │
│  │ GPT-4o      │     │             │     │             │       │
│  └─────────────┘     └─────────────┘     └─────────────┘       │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Redis (:6379) - Session Cache                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  /logs/discussions/ - Agent-Diskussionen (JSON)           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agenten-Architektur

### Orchestrator-Ablauf

```
User-Anfrage
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (MagenticOneGroupChat)                            │
│                                                                  │
│  1. Analysiere Anfrage                                          │
│  2. Erstelle Task-Plan                                          │
│  3. Delegiere an Agenten                                        │
│  4. Überwache Fortschritt (Progress Ledger)                     │
│  5. Erkenne Konsens (2/3 Mehrheit)                              │
│  6. Finalisiere Report                                          │
└─────────────────────────────────────────────────────────────────┘
     │
     ├──► MarketAnalyst: "Analysiere BTCUSDT technisch"
     │         │
     │         ▼ Ergebnis: "RSI 45, EMA bullish, Resistance $43k"
     │
     ├──► NewsResearcher: "Gibt es relevante News?"
     │         │
     │         ▼ Ergebnis: "Fed Meeting morgen, ETF Outflows"
     │
     ├──► MarketAnalyst: "Ändert das deine Einschätzung?" (Soft-Kritik)
     │         │
     │         ▼ Ergebnis: "Ja, besser nach Fed warten"
     │
     ├──► IndicatorCoder: "Berechne optimale Entry-Levels"
     │         │
     │         ├──► CodeExecutor: [führt Python-Code aus]
     │         │
     │         ▼ Ergebnis: "Fib 0.618 bei $41,200"
     │
     ├──► ChartConfigurator: "Erstelle Chart-Config"
     │         │
     │         ▼ Ergebnis: { symbol, indicators, lines }
     │
     └──► ReportWriter: "Fasse Konsens zusammen"
               │
               ▼ FINAL: Markdown Report + Trade-Card
```

### Agenten-Details

| Agent | Basisklasse | System-Prompt Fokus |
|-------|-------------|---------------------|
| **MarketAnalyst** | `AssistantAgent` | Technische Analyse, Trend, Levels. Soft-Kritik: "Bedenke auch..." |
| **NewsResearcher** | `MultimodalWebSurfer` | Web-Recherche, News, Sentiment. Soft-Kritik: "Ergänzend dazu..." |
| **ChartConfigurator** | `AssistantAgent` | Generiert TradingView Widget JSON. Keine Kritik. |
| **ReportWriter** | `AssistantAgent` | Fasst Konsens in Markdown zusammen. Neutral. |
| **IndicatorCoder** | `MagenticOneCoderAgent` | Schreibt Python-Indikatoren. "Alternativ könnte man..." |
| **CodeExecutor** | `CodeExecutorAgent` | Führt Code in Docker aus. Keine Kritik, nur Ergebnisse. |

---

## 📡 WebSocket-Protokoll

### Client → Server

```typescript
interface ClientMessage {
  type: "query";
  message: string;  // z.B. "Analysiere BTC für Swing-Trade"
}
```

### Server → Client

```typescript
// Agenten-Status Updates (für Activity Dots)
interface AgentStatusMessage {
  type: "agent_status";
  agent: "MarketAnalyst" | "NewsResearcher" | "ChartConfigurator" 
       | "ReportWriter" | "IndicatorCoder" | "CodeExecutor";
  active: boolean;
  status?: string;  // z.B. "Prüft RSI..."
}

// Chart-Konfiguration
interface ChartConfigMessage {
  type: "chart_config";
  config: {
    symbol: string;       // "BINANCE:BTCUSDT"
    interval: string;     // "4H"
    indicators: string[]; // ["RSI", "MACD"]
  };
}

// Trade-Empfehlung
interface TradeRecommendation {
  type: "trade_recommendation";
  data: {
    symbol: string;
    direction: "LONG" | "SHORT";
    entry: { min: number; max: number };
    stopLoss: number;
    takeProfit: number[];
    riskReward: string;
    validity: string;
  };
}

// Finaler Report
interface ReportMessage {
  type: "report";
  markdown: string;
}

// Fehler
interface ErrorMessage {
  type: "error";
  message: string;
}
```

---

## 📊 TradingView Widget Integration

### Free Widget (ohne Pro-Account)

```tsx
// Mini Symbol Overview (kostenlos)
<script src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js">
{
  "symbol": "BINANCE:BTCUSDT",
  "width": "100%",
  "height": "220",
  "locale": "de_DE",
  "dateRange": "12M",
  "colorTheme": "dark",
  "isTransparent": false,
  "autosize": true,
  "largeChartUrl": ""
}
</script>

// Technical Analysis Widget (kostenlos)
<script src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js">
{
  "interval": "4h",
  "width": "100%",
  "isTransparent": false,
  "height": "450",
  "symbol": "BINANCE:BTCUSDT",
  "showIntervalTabs": true,
  "displayMode": "single",
  "locale": "de_DE",
  "colorTheme": "dark"
}
</script>
```

### ChartConfigurator Output

```json
{
  "widget": "mini-symbol-overview",
  "symbol": "BINANCE:BTCUSDT",
  "interval": "4H",
  "theme": "dark",
  "indicators": ["RSI", "MACD", "EMA:50", "EMA:200"],
  "levels": [
    { "price": 43000, "type": "resistance", "label": "R1" },
    { "price": 41500, "type": "support", "label": "Entry Zone" }
  ]
}
```

> **Hinweis:** Horizontale Linien können im Free Widget nicht programmatisch gezeichnet werden. 
> Stattdessen zeigt der Report die Levels als Text an.

---

## 📁 Ordnerstruktur (Detail)

```
Trading-FAIT/
├── Planning/
│   ├── MASTER_PLAN.md        # Projektplan mit Phasen
│   ├── STATUS.md             # Aktueller Fortschritt
│   ├── ARCHITECTURE.md       # Dieses Dokument
│   └── RESUME_PROMPT.md      # Prompt für neue Sessions
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Haupt-UI
│   │   ├── layout.tsx        # Root Layout, Providers
│   │   └── globals.css       # Tailwind Basis-Styles
│   ├── components/
│   │   ├── Chat.tsx          # Input-Feld + Send-Button
│   │   ├── ActivityDots.tsx  # 6 Dots für Agenten
│   │   ├── TradingViewWidget.tsx  # Chart Embed
│   │   ├── TradeCard.tsx     # Entry/SL/TP Card
│   │   └── MarkdownReport.tsx  # react-markdown Renderer
│   ├── lib/
│   │   ├── socket.ts         # WebSocket-Client Wrapper
│   │   └── types.ts          # TypeScript Interfaces
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── Dockerfile
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI App Entry
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── websocket.py  # WebSocket-Handler
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── team.py       # TradingAgentTeam Klasse
│   │   │   ├── prompts.py    # System-Prompts
│   │   │   └── termination.py  # TradingTerminationCondition
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── market_data.py  # yfinance + ccxt Wrapper
│   │   │   └── indicators.py   # pandas-ta Indikatoren
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── config.py     # Pydantic Settings
│   │       └── logging.py    # structlog File-Logger
│   ├── requirements.txt
│   └── Dockerfile
│
├── logs/
│   └── discussions/          # Agent-Logs (JSON)
│       └── .gitkeep
│
├── docker-compose.yml        # Entwicklung
├── docker-compose.prod.yml   # Produktion (optional)
├── .env.example              # Umgebungsvariablen Template
├── .gitignore
└── README.md
```

---

## 🔐 Umgebungsvariablen

```bash
# .env.example

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
LOG_LEVEL=INFO
LOG_DIR=./logs/discussions

# Frontend (Next.js)
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/chat

# Redis
REDIS_URL=redis://redis:6379
```

---

## 🐳 Docker-Compose Services

```yaml
# docker-compose.yml
version: '3.9'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_WS_URL=ws://backend:8000/ws/chat
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - ./backend:/app
      - ./logs:/app/logs

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

---

## 📈 Datenfluss

```
1. User tippt: "Trading-Setup für BTC"
                    │
                    ▼
2. Frontend sendet WebSocket: { type: "query", message: "..." }
                    │
                    ▼
3. Backend empfängt, startet MagenticOneGroupChat
                    │
   ┌────────────────┼────────────────┐
   ▼                ▼                ▼
4. Agenten diskutieren (max 20 Turns)
   - Status-Updates → Frontend (Activity Dots)
   - Alle Messages → Log-Datei
                    │
                    ▼
5. Konsens erreicht (2/3 Mehrheit)
                    │
                    ▼
6. ReportWriter erstellt Markdown
                    │
                    ▼
7. Backend sendet:
   - { type: "chart_config", ... }
   - { type: "trade_recommendation", ... }
   - { type: "report", markdown: "..." }
                    │
                    ▼
8. Frontend rendert:
   - TradingView Widget aktualisiert
   - TradeCard erscheint
   - Report wird angezeigt
```

---

## 🔧 Technologie-Stack Zusammenfassung

| Komponente | Technologie | Version |
|------------|-------------|---------|
| Frontend | Next.js | 14.x |
| UI Library | Shadcn/ui + Tailwind | Latest |
| Backend | FastAPI | 0.109+ |
| Python | Python | 3.11+ |
| AI Framework | AutoGen (Magentic-One) | 0.4+ |
| LLM | Azure OpenAI GPT-4o | 2024-02-01 |
| Marktdaten Aktien | yfinance | 0.2.36+ |
| Marktdaten Krypto | ccxt | 4.2+ |
| Indikatoren | pandas-ta | 0.3.14b |
| Cache | Redis | 7.x |
| Container | Docker Compose | 3.9 |
| Logging | structlog | 24.1+ |
