# Resume Prompt für neue Chat-Sessions

> **Zuletzt aktualisiert:** 12.12.2024  
> **Aktueller Status:** Planung abgeschlossen, Phase 1 startet

---

## 🚀 Schnellstart-Prompt

Kopiere den folgenden Prompt und füge ihn in eine neue Chat-Session ein:

---

```
Ich arbeite an dem Projekt "Trading-FAIT" - einer AI-Agenten Trading-Webapp.

**Lies bitte zuerst die Planungsdokumente:**
1. `Planning/MASTER_PLAN.md` - Vollständiger Projektplan mit 9 Phasen
2. `Planning/STATUS.md` - Aktueller Fortschritt und erstellte Dateien
3. `Planning/ARCHITECTURE.md` - Technische Architektur

**Projekt-Zusammenfassung:**
- Containerisierte Trading-Assistenz-Webapp
- Magentic-One (Microsoft AutoGen) als Multi-Agenten-Framework
- 6 Agenten: MarketAnalyst, NewsResearcher, ChartConfigurator, ReportWriter, IndicatorCoder, CodeExecutor
- Azure OpenAI (GPT-4o) als LLM
- Frontend: Next.js 14 + Tailwind + Shadcn/ui
- Backend: FastAPI + WebSocket
- Charts: TradingView Free Widgets
- Marktdaten: yfinance (Aktien) + ccxt (Krypto)

**Wichtige Entscheidungen:**
- ❌ Keine Order-Ausführung - nur Empfehlungen
- ❌ Kein TradingView Pro - Free Widgets
- ❌ Keine Diskussions-UI - nur Logs in Dateien
- ✅ Activity Dots für Agenten-Status (6 subtile Punkte)
- ✅ Soft-Kritik zwischen Agenten
- ✅ Mehrheits-Konsens (2/3 Agenten)
- ✅ max_turns=20, max_stalls=3

**Prüfe STATUS.md für den aktuellen Fortschritt und fahre mit der nächsten offenen Phase fort.**
```

---

## 📋 Detaillierter Resume-Prompt (bei komplexeren Situationen)

```
Ich setze die Arbeit am Projekt "Trading-FAIT" fort.

**Projektkontext:**
Trading-FAIT ist eine AI-Agenten-basierte Webapp zur Unterstützung beim Trading von Aktien und Krypto. 
Das System nutzt Magentic-One (Microsoft AutoGen) mit 6 spezialisierten Agenten, die in mehreren 
Runden miteinander diskutieren, um qualitativ hochwertige Trading-Analysen und Empfehlungen zu liefern.

**Tech-Stack:**
- Backend: FastAPI + Python 3.11 + Magentic-One + Azure OpenAI GPT-4o
- Frontend: Next.js 14 + Tailwind + Shadcn/ui + TradingView Free Widgets
- Marktdaten: yfinance (Aktien), ccxt (Krypto), pandas-ta (Indikatoren)
- Container: Docker Compose (Backend, Frontend, Redis)
- Logging: structlog → JSON-Dateien in /logs/discussions/

**Agenten-Team:**
1. MarketAnalyst - Technische Analyse (RSI, MACD, EMA, Support/Resistance)
2. NewsResearcher (WebSurfer) - News-Recherche, Sentiment
3. ChartConfigurator - TradingView Widget-Konfiguration
4. ReportWriter - Markdown-Reports mit Konsens-Zusammenfassung
5. IndicatorCoder - Custom Python-Indikatoren schreiben
6. CodeExecutor - Code in Docker-Sandbox ausführen

**Termination-Strategie:**
- max_turns=20 (Hard-Limit)
- max_stalls=3 (Wiederholungen ohne Fortschritt)
- Mehrheits-Konsens: 2/3 beteiligte Agenten stimmen zu
- Soft-Kritik: Konstruktiv, schnelle Einigung

**UI-Konzept:**
- Minimalistisch mit Activity Dots (6 Punkte für Agenten-Status)
- TradingView Free Chart Widget
- Trade-Card mit Entry/SL/TP
- Markdown-Report Viewer
- Diskussionen NUR in Logs, nicht im UI

**Planungsdokumente lesen:**
1. Planning/MASTER_PLAN.md
2. Planning/STATUS.md
3. Planning/ARCHITECTURE.md

**Anweisung:**
Lies STATUS.md, identifiziere die aktuelle Phase und den Fortschritt, und fahre mit der Implementierung fort.
Aktualisiere STATUS.md nach jeder abgeschlossenen Aufgabe.
```

---

## 🔄 Nach Abschluss einer Phase

Wenn du eine Phase abgeschlossen hast, aktualisiere `STATUS.md`:

1. Ändere den Phasen-Status von 🔴 auf ✅
2. Aktualisiere den Fortschritt (z.B. 20%, 40%, etc.)
3. Markiere erstellte Dateien als ✅
4. Füge die Aktivität zum "Letzte Aktivitäten" Log hinzu
5. Aktualisiere "Nächste Schritte"

---

## 📌 Status-Legende

| Symbol | Bedeutung |
|--------|-----------|
| 🔴 | Nicht gestartet |
| 🟡 | In Arbeit |
| ✅ | Abgeschlossen |
| ⚠️ | Blocker / Problem |

---

## 🧭 Phasen-Übersicht (Quick Reference)

| Phase | Beschreibung | Dateien |
|-------|--------------|---------|
| 1 | Projektstruktur | Ordner, .env, docker-compose, .gitignore |
| 2 | Backend Core | main.py, config.py, logging.py, requirements.txt |
| 3 | Magentic-One Agenten | team.py, prompts.py, termination.py |
| 4 | Market-Data | market_data.py, indicators.py |
| 5 | WebSocket API | websocket.py |
| 6 | Frontend Basis | layout.tsx, page.tsx, package.json |
| 7 | Frontend Komponenten | Chat, ActivityDots, TradingView, TradeCard, Report |
| 8 | Docker | Dockerfiles, docker-compose vollständig |
| 9 | Testing | End-to-End Tests, Feinschliff |

---

## ⚡ Sofort-Befehle für neue Session

```bash
# Status prüfen
cat Planning/STATUS.md

# Welche Dateien existieren bereits?
find . -type f -name "*.py" -o -name "*.tsx" -o -name "*.ts" | head -50

# Docker-Status
docker-compose ps

# Logs prüfen
ls -la logs/discussions/
```
