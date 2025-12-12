# Trading-FAIT 🤖📈

> AI-Agenten Trading-Webapp mit Magentic-One + Azure OpenAI

Eine containerisierte Trading-Assistenz-Webapp, die mit AI-Agenten natürliche Sprach-Anfragen zu Aktien und Krypto beantwortet. Das System analysiert Märkte, identifiziert Trading-Chancen und liefert konkrete, umsetzbare Empfehlungen.

## ✨ Features

- **Asset-Agnostisch:** Unterstützt Aktien (AAPL, MSFT) und Krypto (BTC, ETH)
- **Natürliche Sprache:** Frage einfach "Welchen Kurs hat Bitcoin?" oder "Erstelle ein Trading-Setup für AAPL"
- **6 spezialisierte AI-Agenten:** Arbeiten zusammen für beste Analyseergebnisse
- **Live-Charts:** TradingView Integration
- **Keine Order-Ausführung:** Nur Empfehlungen - du behältst die Kontrolle

## 🤖 Agenten-Team

| Agent | Aufgabe |
|-------|---------|
| **MarketAnalyst** | Technische Analyse (RSI, MACD, EMA, Support/Resistance) |
| **NewsResearcher** | Web-Recherche, News, Sentiment-Analyse |
| **ChartConfigurator** | TradingView Widget-Konfiguration |
| **ReportWriter** | Markdown-Reports mit Konsens-Zusammenfassung |
| **IndicatorCoder** | Custom Python-Indikatoren schreiben |
| **CodeExecutor** | Code sicher in Sandbox ausführen |

## 🚀 Quick Start

### Voraussetzungen

- Docker & Docker Compose
- Azure OpenAI Zugang (GPT-4o Deployment)

### Installation

1. **Repository klonen:**
   ```bash
   git clone https://github.com/totosan/Trading-FAIT.git
   cd Trading-FAIT
   ```

2. **Umgebungsvariablen konfigurieren:**
   ```bash
   cp .env.example .env
   # Bearbeite .env und füge deine Azure OpenAI Credentials ein
   ```

3. **Starten:**
   ```bash
   docker-compose up --build
   ```

4. **Öffne im Browser:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## 📁 Projektstruktur

```
Trading-FAIT/
├── frontend/          # Next.js 14 Frontend
├── backend/           # FastAPI Backend
├── logs/              # Agent-Diskussionen (JSON)
├── Planning/          # Projektdokumentation
├── docker-compose.yml # Entwicklung
└── docker-compose.prod.yml # Produktion
```

## 🛠️ Tech Stack

| Layer | Technologie |
|-------|-------------|
| Frontend | Next.js 14, Tailwind CSS, Shadcn/ui |
| Backend | FastAPI, Python 3.11 |
| AI Framework | Magentic-One (Microsoft AutoGen) |
| LLM | Azure OpenAI GPT-4o |
| Marktdaten | yfinance (Aktien), ccxt (Krypto) |
| Container | Docker Compose |

## 📖 Dokumentation

Siehe [Planning/MASTER_PLAN.md](Planning/MASTER_PLAN.md) für den vollständigen Projektplan.

## ⚠️ Disclaimer

**Keine Finanzberatung!** Diese Webapp liefert nur Informationen und Analysen. Alle Trading-Entscheidungen triffst du selbst. Investiere nur Geld, dessen Verlust du verkraften kannst.

## 📄 Lizenz

MIT License
