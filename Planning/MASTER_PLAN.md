# Trading-FAIT Master Plan

> **Projekt:** AI-Agenten Trading-Webapp mit Magentic-One + Azure OpenAI  
> **Erstellt:** 12.12.2024  
> **Status:** 🟡 In Planung

---

## 🎯 Projektziel

Eine containerisierte Trading-Assistenz-Webapp, die:
- Aktien und Krypto-Assets **asset-agnostisch** unterstützt
- Natürliche Sprach-Anfragen zu Kursen, Trends und Strategien beantwortet
- **Keine Orders ausführt**, sondern konkrete, umsetzbare Empfehlungen liefert
- Lokal via Docker und in Azure deploybar ist

---

## 📋 Phasen-Übersicht

| Phase | Beschreibung | Status | Geschätzte Dauer |
|-------|--------------|--------|------------------|
| 1 | Projektstruktur & Basis-Setup | 🔴 Nicht gestartet | 1-2 Stunden |
| 2 | Backend Core (FastAPI + Config) | 🔴 Nicht gestartet | 2-3 Stunden |
| 3 | Magentic-One Agenten-Team | 🔴 Nicht gestartet | 3-4 Stunden |
| 4 | Market-Data Services | 🔴 Nicht gestartet | 2 Stunden |
| 5 | WebSocket API & Streaming | 🔴 Nicht gestartet | 2 Stunden |
| 6 | Frontend Basis (Next.js) | 🔴 Nicht gestartet | 2-3 Stunden |
| 7 | Frontend UI-Komponenten | 🔴 Nicht gestartet | 3-4 Stunden |
| 8 | Docker-Compose & Integration | 🔴 Nicht gestartet | 2 Stunden |
| 9 | Testing & Feinschliff | 🔴 Nicht gestartet | 2-3 Stunden |

---

## 📦 Phase 1: Projektstruktur & Basis-Setup

### Ziel
Grundlegende Ordnerstruktur und Konfigurationsdateien anlegen.

### Dateien zu erstellen
```
Trading-FAIT/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agents/
│   │   ├── services/
│   │   └── core/
│   ├── requirements.txt
│   └── Dockerfile
├── logs/
│   └── discussions/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
└── README.md
```

### Akzeptanzkriterien
- [ ] Alle Ordner existieren
- [ ] `.env.example` mit Azure OpenAI Variablen
- [ ] `docker-compose.yml` Basis-Struktur
- [ ] `.gitignore` konfiguriert

---

## ⚙️ Phase 2: Backend Core (FastAPI + Config)

### Ziel
FastAPI-Anwendung mit Azure OpenAI Konfiguration und Logging.

### Dateien
| Datei | Beschreibung |
|-------|--------------|
| `backend/app/main.py` | FastAPI App mit CORS, WebSocket |
| `backend/app/core/config.py` | Pydantic Settings für Azure OpenAI |
| `backend/app/core/logging.py` | structlog File-Logger |
| `backend/requirements.txt` | Alle Python-Dependencies |

### Dependencies
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
websockets>=12.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
structlog>=24.1.0
python-dotenv>=1.0.0
autogen-agentchat>=0.4.0
autogen-ext[magentic-one,openai,azure,web-surfer,docker]>=0.4.0
```

### Akzeptanzkriterien
- [ ] FastAPI startet ohne Fehler
- [ ] Azure OpenAI Config wird geladen
- [ ] Logs werden in `/logs/` geschrieben

---

## 🤖 Phase 3: Magentic-One Agenten-Team

### Ziel
6-Agenten-Team mit Soft-Kritik und Mehrheits-Konsens implementieren.

### Dateien
| Datei | Beschreibung |
|-------|--------------|
| `backend/app/agents/team.py` | `TradingAgentTeam` Klasse mit MagenticOneGroupChat |
| `backend/app/agents/prompts.py` | System-Prompts für alle 6 Agenten |
| `backend/app/agents/termination.py` | `TradingTerminationCondition` mit Konsens-Check |

### Agenten
| Agent | Typ | Aufgabe |
|-------|-----|---------|
| `MarketAnalyst` | AssistantAgent | Technische Analyse, Trend, Support/Resistance |
| `NewsResearcher` | MultimodalWebSurfer | News-Recherche, Sentiment |
| `ChartConfigurator` | AssistantAgent | TradingView Widget-Config generieren |
| `ReportWriter` | AssistantAgent | Markdown-Report mit Konsens |
| `IndicatorCoder` | MagenticOneCoderAgent | Custom Indikatoren schreiben |
| `CodeExecutor` | CodeExecutorAgent | Code in Docker ausführen |

### Termination-Strategie
- `max_turns = 20` (Hard-Limit)
- `max_stalls = 3` (Wiederholungen)
- **Mehrheits-Konsens:** 2 von 3 beteiligten Agenten stimmen zu
- **Soft-Kritik:** Konstruktiv, schnelle Einigung

### Akzeptanzkriterien
- [ ] Alle 6 Agenten initialisiert
- [ ] MagenticOneGroupChat funktioniert
- [ ] Termination beendet nach Konsens
- [ ] Diskussionen werden geloggt

---

## 📊 Phase 4: Market-Data Services

### Ziel
Asset-agnostische Marktdaten-Abstraktion.

### Dateien
| Datei | Beschreibung |
|-------|--------------|
| `backend/app/services/market_data.py` | Unified API für Aktien + Krypto |
| `backend/app/services/indicators.py` | Standard-Indikatoren (RSI, MACD, EMA) |

### APIs
| Asset-Typ | Library | Beispiel |
|-----------|---------|----------|
| Aktien/ETFs | `yfinance` | AAPL, MSFT, SPY |
| Krypto | `ccxt` | BTC/USDT, ETH/USDT |

### Dependencies (zusätzlich)
```
yfinance>=0.2.36
ccxt>=4.2.0
pandas>=2.2.0
pandas-ta>=0.3.14b
```

### Akzeptanzkriterien
- [ ] `get_quote("AAPL")` liefert Aktienkurs
- [ ] `get_quote("BTC/USDT")` liefert Krypto-Kurs
- [ ] `calculate_indicators()` liefert RSI, MACD, EMA

---

## 🔌 Phase 5: WebSocket API & Streaming

### Ziel
Realtime-Kommunikation zwischen Frontend und Agenten.

### Dateien
| Datei | Beschreibung |
|-------|--------------|
| `backend/app/api/websocket.py` | WebSocket-Handler |
| `backend/app/api/routes.py` | REST-Endpoints (optional) |

### WebSocket-Nachrichten
```typescript
// Client → Server
{ "type": "query", "message": "Analysiere BTC" }

// Server → Client
{ "type": "agent_status", "agent": "MarketAnalyst", "active": true }
{ "type": "agent_status", "agent": "MarketAnalyst", "active": false }
{ "type": "chart_config", "config": {...} }
{ "type": "report", "markdown": "# BTC Analyse..." }
{ "type": "trade_recommendation", "data": {...} }
```

### Akzeptanzkriterien
- [ ] WebSocket-Verbindung stabil
- [ ] Agenten-Status wird gestreamt
- [ ] Report wird am Ende geliefert

---

## 🎨 Phase 6: Frontend Basis (Next.js)

### Ziel
Next.js 14 Projekt mit Tailwind und Shadcn/ui Setup.

### Dateien
| Datei | Beschreibung |
|-------|--------------|
| `frontend/app/layout.tsx` | Root Layout mit Providers |
| `frontend/app/page.tsx` | Haupt-UI |
| `frontend/app/globals.css` | Tailwind Styles |
| `frontend/lib/socket.ts` | WebSocket-Client |
| `frontend/lib/types.ts` | TypeScript Types |

### Setup-Schritte
1. Next.js 14 mit App Router
2. Tailwind CSS
3. Shadcn/ui Komponenten
4. Socket.io-client

### Akzeptanzkriterien
- [ ] Next.js startet
- [ ] Tailwind funktioniert
- [ ] WebSocket-Verbindung zum Backend

---

## 🧩 Phase 7: Frontend UI-Komponenten

### Ziel
Alle UI-Komponenten für das Trading-Interface.

### Komponenten
| Komponente | Beschreibung |
|------------|--------------|
| `Chat.tsx` | Eingabefeld für Fragen |
| `ActivityDots.tsx` | 6 Dots für Agenten-Status |
| `TradingViewWidget.tsx` | TradingView Free Chart |
| `TradeCard.tsx` | Entry/SL/TP Empfehlung |
| `MarkdownReport.tsx` | Report-Renderer |

### ActivityDots Design
```
○ ○ ○ ○ ○ ○   (Ruhe)
● ○ ○ ○ ○ ○   (MarketAnalyst aktiv)
● ● ○ ○ ○ ○   (Diskussion)
```

### Akzeptanzkriterien
- [ ] Chat-Input funktioniert
- [ ] Activity Dots zeigen Status
- [ ] TradingView Chart lädt
- [ ] Report wird gerendert

---

## 🐳 Phase 8: Docker-Compose & Integration

### Ziel
Vollständige Container-Orchestrierung.

### Services
| Service | Image/Build | Ports |
|---------|-------------|-------|
| `frontend` | Build ./frontend | 3000 |
| `backend` | Build ./backend | 8000 |
| `redis` | redis:alpine | 6379 |

### Dateien
| Datei | Beschreibung |
|-------|--------------|
| `docker-compose.yml` | Entwicklung (Hot-Reload) |
| `docker-compose.prod.yml` | Produktion |
| `frontend/Dockerfile` | Next.js Container |
| `backend/Dockerfile` | FastAPI + Playwright |

### Akzeptanzkriterien
- [ ] `docker-compose up` startet alles
- [ ] Frontend erreicht Backend
- [ ] Playwright funktioniert für WebSurfer

---

## 🧪 Phase 9: Testing & Feinschliff

### Ziel
End-to-End Test und Optimierungen.

### Tests
- [ ] Einfache Kursabfrage: "Was kostet Apple?"
- [ ] Trend-Analyse: "Welcher Trend bei BTC?"
- [ ] Strategie-Anfrage: "Trading-Setup für ETH"
- [ ] Multi-Agent Diskussion funktioniert
- [ ] Report wird korrekt generiert

### Optimierungen
- [ ] Fehlerbehandlung
- [ ] Loading States
- [ ] Responsive Design

---

## 🔧 Technische Entscheidungen

| Entscheidung | Wahl | Begründung |
|--------------|------|------------|
| LLM Provider | Azure OpenAI | Enterprise, DSGVO |
| Modell | GPT-4o | Multimodal für WebSurfer |
| Agent Framework | Magentic-One | Multi-Agent, Orchestrator |
| Frontend | Next.js 14 | Modern, SSR, WebSocket |
| Charts | TradingView Free | Kein Pro-Account nötig |
| Kritik-Stil | Soft | Schnelle Einigung |
| Konsens | Mehrheit (2/3) | Effizient |
| Diskussions-Logs | Datei (JSON) | Einfach, kein UI |

---

## 📝 Offene Fragen (Geklärt)

| Frage | Antwort |
|-------|---------|
| Orders ausführen? | ❌ Nein, nur Empfehlungen |
| TradingView Pro? | ❌ Nein, Free Widgets |
| Diskussion im UI? | ❌ Nein, nur Logs |
| Agenten-Aktivität? | ✅ Activity Dots (subtil) |
| Kritik-Stil? | Soft (konstruktiv) |
| Konsens-Regel? | Mehrheit (2 von 3) |
| Log-Speicherung? | Datei, keine DB |
