# Trading-FAIT Makefile
# Einfache Befehle zum Starten und Verwalten der Applikation

.PHONY: dev dev-backend dev-frontend install install-backend install-frontend stop clean logs test help

# Farben für Output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# ========================================
# Development
# ========================================

dev: ## Startet Backend und Frontend parallel
	@echo "$(GREEN)🚀 Starting Trading-FAIT...$(NC)"
	@$(MAKE) -j2 dev-backend dev-frontend
	@echo "$(GREEN)✅ Trading-FAIT is running!$(NC)"
	@echo "$(BLUE)Frontend: http://localhost:3000$(NC)"
	@echo "$(BLUE)Backend:  http://localhost:8000$(NC)"
	@echo "$(BLUE)API Docs: http://localhost:8000/docs$(NC)"

dev-backend: ## Startet nur das Backend
	@echo "$(BLUE)🔧 Starting Backend...$(NC)"
	@cd backend && \
		export $$(grep -v '^#' ../.env | xargs) && \
		uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## Startet nur das Frontend
	@echo "$(BLUE)🎨 Starting Frontend...$(NC)"
	@cd frontend && npm run dev

# ========================================
# Installation
# ========================================

install: install-backend install-frontend ## Installiert alle Dependencies
	@echo "$(GREEN)✅ All dependencies installed!$(NC)"

install-backend: ## Installiert Backend Dependencies
	@echo "$(BLUE)📦 Installing Backend dependencies...$(NC)"
	@cd backend && pip install -r requirements.txt -q
	@echo "$(GREEN)✅ Backend dependencies installed$(NC)"

install-frontend: ## Installiert Frontend Dependencies
	@echo "$(BLUE)📦 Installing Frontend dependencies...$(NC)"
	@cd frontend && npm install
	@echo "$(GREEN)✅ Frontend dependencies installed$(NC)"

# ========================================
# Docker
# ========================================

docker-dev: ## Startet die Applikation in Docker (Development)
	@echo "$(BLUE)🐳 Starting Docker containers...$(NC)"
	@docker-compose up --build

docker-up: ## Startet Docker Container im Hintergrund
	@docker-compose up -d --build
	@echo "$(GREEN)✅ Docker containers started$(NC)"

docker-down: ## Stoppt Docker Container
	@docker-compose down
	@echo "$(YELLOW)⏹️  Docker containers stopped$(NC)"

docker-logs: ## Zeigt Docker Logs
	@docker-compose logs -f

# ========================================
# Utilities
# ========================================

stop: ## Stoppt alle laufenden Prozesse
	@echo "$(YELLOW)⏹️  Stopping all processes...$(NC)"
	@pkill -f uvicorn 2>/dev/null || true
	@pkill -f "next dev" 2>/dev/null || true
	@pkill -f "npm run dev" 2>/dev/null || true
	@echo "$(GREEN)✅ All processes stopped$(NC)"

clean: stop ## Stoppt Prozesse und räumt auf
	@echo "$(YELLOW)🧹 Cleaning up...$(NC)"
	@rm -rf backend/__pycache__ backend/app/__pycache__ 2>/dev/null || true
	@rm -rf backend/logs/discussions/*.json 2>/dev/null || true
	@rm -rf frontend/.next 2>/dev/null || true
	@rm -rf frontend/node_modules/.cache 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

logs: ## Zeigt Backend Logs
	@echo "$(BLUE)📋 Recent discussion logs:$(NC)"
	@ls -la backend/logs/discussions/ 2>/dev/null || echo "No logs yet"
	@echo ""
	@echo "$(BLUE)📋 Latest log content:$(NC)"
	@cat $$(ls -t backend/logs/discussions/*.json 2>/dev/null | head -1) 2>/dev/null | head -50 || echo "No logs yet"

# ========================================
# Testing
# ========================================

test: ## Führt alle Tests aus
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	@cd backend && python -m pytest tests/ -v 2>/dev/null || echo "No tests yet"

test-backend: ## Testet Backend Health
	@echo "$(BLUE)🔍 Testing Backend...$(NC)"
	@curl -s http://localhost:8000/health | python3 -m json.tool
	@echo ""
	@curl -s http://localhost:8000/quote/AAPL | python3 -m json.tool

test-ws: ## Testet WebSocket Verbindung
	@echo "$(BLUE)🔌 Testing WebSocket...$(NC)"
	@python3 -c "import asyncio; import websockets; asyncio.run(websockets.connect('ws://localhost:8000/ws'))" && echo "$(GREEN)✅ WebSocket OK$(NC)" || echo "$(RED)❌ WebSocket failed$(NC)"

# ========================================
# Environment
# ========================================

env-check: ## Prüft Umgebungsvariablen
	@echo "$(BLUE)🔍 Checking environment...$(NC)"
	@test -f .env && echo "$(GREEN)✅ .env file exists$(NC)" || echo "$(RED)❌ .env file missing - copy from .env.example$(NC)"
	@grep -q "AZURE_OPENAI_ENDPOINT" .env 2>/dev/null && echo "$(GREEN)✅ Azure OpenAI Endpoint configured$(NC)" || echo "$(RED)❌ Azure OpenAI Endpoint missing$(NC)"
	@grep -q "AZURE_OPENAI_API_KEY" .env 2>/dev/null && echo "$(GREEN)✅ Azure OpenAI API Key configured$(NC)" || echo "$(RED)❌ Azure OpenAI API Key missing$(NC)"

env-setup: ## Erstellt .env aus .env.example
	@test -f .env || cp .env.example .env
	@echo "$(GREEN)✅ .env file ready - please edit with your credentials$(NC)"

# ========================================
# Help
# ========================================

help: ## Zeigt diese Hilfe
	@echo ""
	@echo "$(GREEN)Trading-FAIT$(NC) - AI Trading Assistant"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC)"
	@echo "  make <target>"
	@echo ""
	@echo "$(YELLOW)Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Quick Start:$(NC)"
	@echo "  1. make env-setup     # Setup .env file"
	@echo "  2. make install       # Install dependencies"
	@echo "  3. make dev           # Start the application"
	@echo ""
