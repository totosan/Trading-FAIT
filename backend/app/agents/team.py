"""
Trading-FAIT Agent Team
Magentic-One based multi-agent team for trading analysis
"""

import asyncio
import json
import re
from typing import AsyncGenerator
from dataclasses import dataclass

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.messages import AgentEvent, ChatMessage
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

from ..core.config import get_settings
from ..core.logging import DiscussionFileLogger, get_logger
from ..services.market_data import get_market_data_service
from .prompts import AGENT_PROMPTS, AGENT_DESCRIPTIONS
from .termination import TradingTerminationCondition

logger = get_logger(__name__)


@dataclass
class AgentStatus:
    """Status of an individual agent"""
    name: str
    active: bool = False
    last_message: str | None = None
    message_count: int = 0


@dataclass
class TeamStatus:
    """Overall team status"""
    initialized: bool = False
    running: bool = False
    current_query: str | None = None
    agents: dict[str, AgentStatus] | None = None
    error: str | None = None


class TradingAgentTeam:
    """
    Magentic-One based trading analysis team.
    
    6 specialized agents discuss trading queries and reach consensus:
    - MarketAnalyst: Technical analysis
    - NewsResearcher: Fundamental analysis (WebSurfer capabilities)
    - ChartConfigurator: TradingView chart configuration
    - ReportWriter: Synthesizes analysis into reports
    - IndicatorCoder: Custom indicator code
    - CodeExecutor: Safely executes analysis code
    """
    
    AGENT_NAMES = [
        "MarketAnalyst",
        "NewsResearcher", 
        "ChartConfigurator",
        "ReportWriter",
        "IndicatorCoder",
        "CodeExecutor",
    ]
    
    def __init__(self):
        self._settings = get_settings()
        self._model_client: AzureOpenAIChatCompletionClient | None = None
        self._agents: dict[str, AssistantAgent] = {}
        self._team: MagenticOneGroupChat | None = None
        self._termination: TradingTerminationCondition | None = None
        self._discussion_logger: DiscussionFileLogger | None = None
        self._status = TeamStatus()
        self._current_session_id: str | None = None
        self._trade_emitted: bool = False
        self._chart_emitted: bool = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if team is initialized and ready"""
        return self._status.initialized and self._team is not None
    
    @property
    def status(self) -> TeamStatus:
        """Get current team status"""
        return self._status
    
    def _create_model_client(self) -> AzureOpenAIChatCompletionClient:
        """Create Azure OpenAI client"""
        if not self._settings.is_configured:
            raise ValueError("Azure OpenAI is not configured. Check environment variables.")
        
        # Model info for custom/non-standard model names
        # This is required when the deployment name doesn't match a known OpenAI model
        model_info = {
            "vision": True,  # GPT-4o and newer support vision
            "function_calling": True,
            "json_output": True,
            "family": "gpt-4o",  # Token counting family
        }
        
        return AzureOpenAIChatCompletionClient(
            azure_endpoint=self._settings.azure_openai_endpoint,
            api_key=self._settings.azure_openai_api_key,
            azure_deployment=self._settings.azure_openai_deployment,
            api_version=self._settings.azure_openai_api_version,
            model=self._settings.azure_openai_model,
            model_info=model_info,
        )
    
    def _create_agents(self) -> dict[str, AssistantAgent]:
        """Create all trading agents"""
        agents = {}
        
        for name in self.AGENT_NAMES:
            agent = AssistantAgent(
                name=name,
                model_client=self._model_client,
                system_message=AGENT_PROMPTS[name],
                description=AGENT_DESCRIPTIONS[name],
            )
            agents[name] = agent
            logger.info(f"Created agent: {name}")
        
        return agents
    
    def _create_team(self) -> MagenticOneGroupChat:
        """Create the Magentic-One group chat team"""
        self._termination = TradingTerminationCondition(
            max_turns=self._settings.agent_max_turns,
            max_stalls=self._settings.agent_max_stalls,
            total_agents=len(self.AGENT_NAMES),
        )
        
        # Combine custom termination with max message backup
        max_message_termination = MaxMessageTermination(
            max_messages=self._settings.agent_max_turns * 2
        )
        
        team = MagenticOneGroupChat(
            participants=list(self._agents.values()),
            model_client=self._model_client,
            termination_condition=self._termination | max_message_termination,
            max_stalls=self._settings.agent_max_stalls,
        )
        
        logger.info(
            "Created MagenticOneGroupChat team",
            agent_count=len(self._agents),
            max_turns=self._settings.agent_max_turns,
        )
        
        return team
    
    def _extract_symbols(self, query: str) -> list[str]:
        """
        Extract potential trading symbols from user query.
        
        Looks for:
        - Stock tickers: AAPL, MSFT, GOOGL (2-5 uppercase letters)
        - Company names mapped to tickers (US, EU, etc.)
        - Crypto pairs: BTC/USDT, ETH/USD (with /)
        - Common crypto: Bitcoin, Ethereum, etc.
        """
        symbols = []
        query_upper = query.upper()
        
        # Company names (multi-word first, then single word)
        # Format: (search_term, ticker, is_word_match_only)
        COMPANY_NAMES = [
            # Multi-word company names (search as substring)
            ("NOVO NORDISK", "NVO", False),
            ("MORGAN STANLEY", "MS", False),
            ("DEUTSCHE BANK", "DBK.DE", False),
            ("CREDIT SUISSE", "CS", False),
            ("RIO TINTO", "RIO.L", False),
            # Single-word company names (word boundary match)
            ("NOVONORDISK", "NVO", False),
            ("APPLE", "AAPL", True),
            ("MICROSOFT", "MSFT", True),
            ("GOOGLE", "GOOGL", True),
            ("ALPHABET", "GOOGL", True),
            ("AMAZON", "AMZN", True),
            ("TESLA", "TSLA", True),
            ("NVIDIA", "NVDA", True),
            ("FACEBOOK", "META", True),
            ("NETFLIX", "NFLX", True),
            ("INTEL", "INTC", True),
            ("SALESFORCE", "CRM", True),
            ("ORACLE", "ORCL", True),
            ("PAYPAL", "PYPL", True),
            ("COINBASE", "COIN", True),
            ("DISNEY", "DIS", True),
            ("SHOPIFY", "SHOP", True),
            ("BOEING", "BA", True),
            ("JPMORGAN", "JPM", True),
            ("GOLDMAN", "GS", True),
            ("VISA", "V", True),
            ("MASTERCARD", "MA", True),
            ("WALMART", "WMT", True),
            ("EXXON", "XOM", True),
            ("CHEVRON", "CVX", True),
            # European companies
            ("SIEMENS", "SIE.DE", True),
            ("VOLKSWAGEN", "VOW3.DE", True),
            ("MERCEDES", "MBG.DE", True),
            ("DAIMLER", "MBG.DE", True),
            ("BAYER", "BAYN.DE", True),
            ("BASF", "BAS.DE", True),
            ("ALLIANZ", "ALV.DE", True),
            ("ADIDAS", "ADS.DE", True),
            ("LVMH", "MC.PA", True),
            ("LOREAL", "OR.PA", True),
            ("AIRBUS", "AIR.PA", True),
            ("SANOFI", "SAN.PA", True),
            ("HERMES", "RMS.PA", True),
            ("SHELL", "SHEL.L", True),
            ("ASTRAZENECA", "AZN.L", True),
            ("UNILEVER", "ULVR.L", True),
            ("DIAGEO", "DGE.L", True),
            ("GLENCORE", "GLEN.L", True),
            ("NESTLE", "NESN.SW", True),
            ("NOVARTIS", "NOVN.SW", True),
            ("ROCHE", "ROG.SW", True),
            ("ASML", "ASML", True),
            ("PHILIPS", "PHG", True),
            ("TOTALENERGIES", "TTE.PA", True),
            # Crypto names
            ("BITCOIN", "BTC/USDT", True),
            ("ETHEREUM", "ETH/USDT", True),
            ("SOLANA", "SOL/USDT", True),
            ("RIPPLE", "XRP/USDT", True),
            ("CARDANO", "ADA/USDT", True),
            ("DOGECOIN", "DOGE/USDT", True),
            ("AVALANCHE", "AVAX/USDT", True),
            ("POLKADOT", "DOT/USDT", True),
            ("POLYGON", "MATIC/USDT", True),
            ("CHAINLINK", "LINK/USDT", True),
            ("COSMOS", "ATOM/USDT", True),
            ("LITECOIN", "LTC/USDT", True),
            ("UNISWAP", "UNI/USDT", True),
            ("ARBITRUM", "ARB/USDT", True),
            ("OPTIMISM", "OP/USDT", True),
        ]
        
        # Known stock tickers (direct ticker matches, 2+ chars)
        STOCK_TICKERS = {
            # US stocks
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "NVDA", "META",
            "NFLX", "AMD", "INTC", "CRM", "ORCL", "IBM", "PYPL", "COIN",
            "DIS", "UBER", "LYFT", "SNAP", "SPOT", "ZM", "SHOP", "BA",
            "JPM", "GS", "WMT", "PG", "JNJ", "XOM", "CVX",
            # ADRs and international stocks traded on US exchanges
            "NVO",  # Novo Nordisk ADR
            "SAP",  # SAP
            "AZN",  # AstraZeneca ADR
            "CS",   # Credit Suisse
            "ASML", # ASML
            "PHG",  # Philips
        }
        
        # European stocks (with exchange suffix)
        EU_STOCK_TICKERS = {
            "SIE": "SIE.DE", "VOW3": "VOW3.DE", "BMW": "BMW.DE",
            "MBG": "MBG.DE", "BAYN": "BAYN.DE", "BAS": "BAS.DE",
            "ALV": "ALV.DE", "DBK": "DBK.DE", "ADS": "ADS.DE",
            "MC": "MC.PA", "OR": "OR.PA", "TTE": "TTE.PA",
            "AIR": "AIR.PA", "SAN": "SAN.PA", "RMS": "RMS.PA",
            "SHEL": "SHEL.L", "BP": "BP.L", "HSBA": "HSBA.L",
            "ULVR": "ULVR.L", "DGE": "DGE.L", "GLEN": "GLEN.L",
            "RIO": "RIO.L", "NESN": "NESN.SW", "NOVN": "NOVN.SW",
            "ROG": "ROG.SW", "UBSG": "UBSG.SW",
        }
        
        # Known crypto tickers
        CRYPTO_TICKERS = {
            "BTC": "BTC/USDT", "ETH": "ETH/USDT", "SOL": "SOL/USDT",
            "XRP": "XRP/USDT", "ADA": "ADA/USDT", "DOGE": "DOGE/USDT",
            "AVAX": "AVAX/USDT", "DOT": "DOT/USDT", "MATIC": "MATIC/USDT",
            "LINK": "LINK/USDT", "ATOM": "ATOM/USDT", "LTC": "LTC/USDT",
            "UNI": "UNI/USDT", "AAVE": "AAVE/USDT", "ARB": "ARB/USDT",
            "OP": "OP/USDT",
        }
        
        # 1. Check for crypto pairs with / first (highest priority)
        crypto_pattern = r'\b([A-Z]{2,5})/([A-Z]{3,4})\b'
        for match in re.finditer(crypto_pattern, query_upper):
            pair = f"{match.group(1)}/{match.group(2)}"
            if pair not in symbols:
                symbols.append(pair)
        
        # 2. Check for company names (multi-word and single-word)
        for search_term, ticker, word_match_only in COMPANY_NAMES:
            if word_match_only:
                # Use word boundary matching
                pattern = r'\b' + re.escape(search_term) + r'\b'
                if re.search(pattern, query_upper) and ticker not in symbols:
                    symbols.append(ticker)
            else:
                # Simple substring match for multi-word names
                if search_term in query_upper and ticker not in symbols:
                    symbols.append(ticker)
        
        # 3. Check for standalone tickers (2-5 uppercase letters with word boundaries)
        ticker_pattern = r'\b([A-Z]{2,5})\b'
        common_words = {
            "THE", "AND", "FOR", "BUY", "SELL", "USD", "EUR", "USDT", "WAS", 
            "VON", "DER", "DIE", "DAS", "MIT", "ENDE", "TAG", "KURS",
            "EINE", "EINEN", "EINEM", "MACHE", "BITTE", "ZEIGE", "ANALYSE",
            "AKTIE", "CHART", "PREIS", "NEWS", "LONG", "SHORT", "STOP", "TAKE",
            "ABOUT", "WHAT", "HOW", "CAN", "GIVE", "SHOW", "TELL", "MAKE",
            "PLEASE", "HELP", "FROM", "WITH", "THIS", "THAT", "HAVE", "WILL",
        }
        
        for match in re.finditer(ticker_pattern, query_upper):
            ticker = match.group(1)
            if ticker in common_words:
                continue
            
            # Check if it's a known stock ticker
            if ticker in STOCK_TICKERS and ticker not in symbols:
                symbols.append(ticker)
            # Check EU stocks
            elif ticker in EU_STOCK_TICKERS and EU_STOCK_TICKERS[ticker] not in symbols:
                symbols.append(EU_STOCK_TICKERS[ticker])
            # Check crypto tickers
            elif ticker in CRYPTO_TICKERS and CRYPTO_TICKERS[ticker] not in symbols:
                symbols.append(CRYPTO_TICKERS[ticker])
        
        return symbols[:3]  # Limit to 3 symbols
    
    async def _enrich_query_with_market_data(
        self,
        query: str,
        symbols: list[str] | None = None,
    ) -> str:
        """
        Enrich user query with real-time market data.
        
        Extracts symbols from the query, fetches current market data,
        and prepends it to the query for agent context.
        """
        symbols = symbols or self._extract_symbols(query)
        
        if not symbols:
            return query
        
        market_service = get_market_data_service()
        market_context_parts = ["=== LIVE MARKET DATA (fetched just now) ===\n"]
        
        for symbol in symbols:
            try:
                quote = await market_service.get_quick_quote(symbol)
                
                if quote.get("error"):
                    market_context_parts.append(f"❌ {symbol}: Data unavailable - {quote['error']}\n")
                else:
                    price = quote.get("price")
                    change_pct = quote.get("change_24h_pct")
                    high = quote.get("high_24h")
                    low = quote.get("low_24h")
                    volume = quote.get("volume_24h")
                    
                    change_str = f"{change_pct:+.2f}%" if change_pct else "N/A"
                    price_str = f"${price:,.2f}" if price else "N/A"
                    high_str = f"${high:,.2f}" if high else "N/A"
                    low_str = f"${low:,.2f}" if low else "N/A"
                    
                    market_context_parts.append(
                        f"📊 {symbol} ({quote.get('asset_type', 'unknown').upper()})\n"
                        f"   Current Price: {price_str}\n"
                        f"   24h Change: {change_str}\n"
                        f"   24h High/Low: {high_str} / {low_str}\n"
                    )
                    
                    if volume:
                        vol_str = f"${volume:,.0f}" if volume > 1000 else f"{volume:.2f}"
                        market_context_parts.append(f"   24h Volume: {vol_str}\n")
                    
                    market_context_parts.append("\n")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch market data for {symbol}: {e}")
                market_context_parts.append(f"⚠️ {symbol}: Could not fetch data\n")
        
        market_context_parts.append("=== END MARKET DATA ===\n\n")
        market_context_parts.append("User Query: " + query)
        
        return "".join(market_context_parts)

    def _parse_trade_recommendation(self, content: str, symbols: list[str]) -> tuple[dict | None, dict | None]:
        """
        Heuristic parser to extract trade recommendation and chart levels from agent text.
        Emits only when we find entry + stop + take profit.
        """
        # 1) Try structured JSON block first
        try:
            json_match = re.search(r"\{[\s\S]*\}\s*$", content)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if "trade_recommendation" in parsed:
                    tr = parsed.get("trade_recommendation", {})
                    ch = parsed.get("chart_config")

                    entry_val = tr.get("entry")
                    # Normalize entry if array -> range
                    if isinstance(entry_val, list) and len(entry_val) >= 2:
                        entry_val = {"min": float(entry_val[0]), "max": float(entry_val[1])}

                    tp_val = tr.get("takeProfit") or tr.get("takeProfits")
                    tp_list: list[float] = []
                    if isinstance(tp_val, list):
                        tp_list = [float(x) for x in tp_val if x is not None]
                    elif tp_val is not None:
                        tp_list = [float(tp_val)]

                    stop_val = tr.get("stopLoss")

                    # Build trade dict
                    trade = {
                        "symbol": tr.get("symbol") or (symbols[0] if symbols else ""),
                        "direction": (tr.get("direction") or "LONG").upper(),
                        "entry": entry_val,
                        "stopLoss": float(stop_val) if stop_val is not None else None,
                        "takeProfit": tp_list if len(tp_list) > 1 else (tp_list[0] if tp_list else None),
                        "riskReward": tr.get("riskReward") or "n/a",
                    }

                    # Build chart config (use provided or synthesize)
                    chart_cfg = None
                    if ch:
                        chart_cfg = ch
                    else:
                        entries_list: list[float] = []
                        if isinstance(entry_val, list):
                            entries_list = [float(x) for x in entry_val if x is not None]
                        elif isinstance(entry_val, dict):
                            if entry_val.get("min") is not None:
                                entries_list.append(float(entry_val["min"]))
                            if entry_val.get("max") is not None:
                                entries_list.append(float(entry_val["max"]))
                        elif entry_val is not None:
                            entries_list = [float(entry_val)]

                        chart_cfg = {
                            "symbol": trade["symbol"],
                            "interval": "D",
                            "indicators": ["EMA50", "EMA200", "RSI"],
                            "theme": "dark",
                            "priceLevels": {
                                "entries": entries_list,
                                "stopLoss": trade["stopLoss"],
                                "takeProfits": tp_list,
                            },
                        }

                    # If numbers missing, fall back to heuristics
                    if trade["entry"] is not None and trade["stopLoss"] is not None and tp_list:
                        return trade, chart_cfg
        except Exception:
            # Fallback to heuristic parsing below
            pass
        text_lower = content.lower()

        # Determine direction
        direction: str | None = None
        if "short" in text_lower and "long" not in text_lower:
            direction = "SHORT"
        elif "long" in text_lower and "short" not in text_lower:
            direction = "LONG"
        elif "short" in text_lower and "long" in text_lower:
            # Pick the one that appears first
            direction = "LONG" if text_lower.find("long") < text_lower.find("short") else "SHORT"

        number_pattern = r"\d+[\.,]?\d*"

        def _to_float(value: str) -> float:
            cleaned = value.replace(" ", "").replace(",", ".")
            return float(cleaned) if cleaned else 0.0

        entry_match = re.search(r"(entry|einstieg)[^\d]*((?:" + number_pattern + ")(?:\s*-\s*(?:" + number_pattern + "))?)", text_lower)
        entry_value: float | dict | None = None
        entry_list: list[float] = []
        if entry_match:
            raw_entry = entry_match.group(2)
            if "-" in raw_entry:
                parts = [p.strip() for p in raw_entry.split("-") if p.strip()]
                if len(parts) == 2:
                    low, high = _to_float(parts[0]), _to_float(parts[1])
                    entry_value = {"min": min(low, high), "max": max(low, high)}
                    entry_list = [min(low, high), max(low, high)]
            else:
                val = _to_float(raw_entry)
                entry_value = val
                entry_list = [val]

        stop_match = re.search(r"stop[^\d]*((?:" + number_pattern + "))", text_lower)
        stop_value: float | None = None
        if stop_match:
            stop_value = _to_float(stop_match.group(1))

        # Capture multiple take profits (TP1/TP2) or a single take profit
        tp_values: list[float] = []
        for m in re.finditer(r"tp\d?[^\d]*((?:" + number_pattern + "))", text_lower):
            try:
                tp_values.append(_to_float(m.group(1)))
            except Exception:
                continue

        if not tp_values:
            tp_match = re.search(r"take\s*profit[^\d]*((?:" + number_pattern + "))", text_lower)
            if tp_match:
                tp_values.append(_to_float(tp_match.group(1)))

        if entry_value is None or stop_value is None or not tp_values:
            return None, None

        symbol = symbols[0] if symbols else ""

        # Plausibility filter to avoid picking tiny % numbers as prices
        values_for_scale: list[float] = []
        if isinstance(entry_value, dict):
            if entry_value.get("min") is not None:
                values_for_scale.append(float(entry_value["min"]))
            if entry_value.get("max") is not None:
                values_for_scale.append(float(entry_value["max"]))
        else:
            values_for_scale.append(float(entry_value))
        values_for_scale.append(float(stop_value))
        values_for_scale.extend([float(x) for x in tp_values])

        # Reject if any non-positive or scale is wildly inconsistent (>50x spread)
        if any(v <= 0 for v in values_for_scale):
            return None, None
        if max(values_for_scale) / min(values_for_scale) > 50:
            return None, None

        def _risk_reward(direction: str | None, entry_val: float | dict | None, stop: float, tp_list: list[float]) -> str:
            if entry_val is None or not tp_list:
                return "n/a"
            # Use midpoint for ranges
            if isinstance(entry_val, dict):
                mid = (entry_val.get("min", 0.0) + entry_val.get("max", 0.0)) / 2
                entry_num = mid
            else:
                entry_num = float(entry_val)
            tp_num = tp_list[0]
            if direction == "SHORT":
                risk = entry_num - stop
                reward = entry_num - tp_num
            else:
                risk = entry_num - stop
                reward = tp_num - entry_num
            if risk <= 0 or reward <= 0:
                return "n/a"
            ratio = reward / risk
            # Round to one decimal (e.g., 2.5R)
            return f"{ratio:.1f}:1"

        trade = {
            "symbol": symbol,
            "direction": direction or "LONG",
            "entry": entry_value,
            "stopLoss": stop_value,
            "takeProfit": tp_values if len(tp_values) > 1 else tp_values[0],
            "riskReward": _risk_reward(direction, entry_value, stop_value, tp_values),
        }

        chart_config = {
            "symbol": symbol,
            "interval": "D",
            "indicators": ["EMA50", "EMA200", "RSI"],
            "theme": "dark",
            "priceLevels": {
                "entries": entry_list if entry_list else None,
                "stopLoss": stop_value,
                "takeProfits": tp_values,
            },
        }

        return trade, chart_config
    
    async def initialize(self) -> None:
        """Initialize the agent team"""
        try:
            logger.info("Initializing Trading Agent Team...")
            
            # Create model client
            self._model_client = self._create_model_client()
            logger.info("Azure OpenAI client created")
            
            # Create agents
            self._agents = self._create_agents()
            
            # Initialize agent statuses
            self._status.agents = {
                name: AgentStatus(name=name) 
                for name in self.AGENT_NAMES
            }
            
            # Create team
            self._team = self._create_team()
            
            self._status.initialized = True
            self._status.error = None
            logger.info("Trading Agent Team initialized successfully")
            
        except Exception as e:
            self._status.initialized = False
            self._status.error = str(e)
            logger.error(f"Failed to initialize agent team: {e}")
            raise
    
    async def run_query(
        self, 
        query: str,
        session_id: str | None = None,
        conversation_context: str | None = None,
        symbols_override: list[str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Run a trading query through the agent team.
        
        Yields status updates and agent messages as they occur.
        
        Args:
            query: The trading query (e.g., "Analyze BTC/USDT")
            session_id: Optional session ID for logging
            conversation_context: Optional context from previous conversation turns
            
        Yields:
            Dict with message type and content
        """
        if not self.is_initialized:
            await self.initialize()
        
        self._status.running = True
        self._status.current_query = query
        self._trade_emitted = False
        self._chart_emitted = False
        
        # Setup discussion logger
        import uuid
        self._current_session_id = session_id or str(uuid.uuid4())
        self._discussion_logger = DiscussionFileLogger(
            session_id=self._current_session_id,
        )
        
        # Log the original user query
        self._discussion_logger.log_agent_message(
            agent="user",
            message=query,
            round_num=1,
        )
        
        logger.info(
            "Starting agent discussion",
            session_id=self._current_session_id,
            query=query[:100],
        )
        
        try:
            # Enrich query with real-time market data
            enriched_query = await self._enrich_query_with_market_data(
                query,
                symbols=symbols_override,
            )
            logger.info(
                "Query enriched with market data",
                symbols=symbols_override or self._extract_symbols(query)
            )
            
            # Add conversation context if provided (token-efficient)
            if conversation_context:
                enriched_query = (
                    "=== CONVERSATION CONTEXT (previous discussion) ===\n"
                    f"{conversation_context}\n"
                    "=== END CONTEXT ===\n\n"
                    f"{enriched_query}"
                )
                logger.info("Query enriched with conversation context")
            
            # Reset termination condition for new query
            await self._termination.reset()
            
            # Reset agent statuses
            for agent_status in self._status.agents.values():
                agent_status.active = False
                agent_status.message_count = 0
            
            # Track round number
            round_num = 0
            
            # Yield initial status
            yield {
                "type": "query_start",
                "session_id": self._current_session_id,
                "query": query,
            }
            
            # Run the team with streaming (using enriched query with market data)
            async for message in self._team.run_stream(task=enriched_query):
                # Handle different message types
                # TaskResult has 'messages' list, regular messages have 'content'
                
                # Skip TaskResult objects - they contain the final summary
                # but we already streamed individual messages
                if hasattr(message, 'messages') and hasattr(message, 'stop_reason'):
                    # This is a TaskResult - skip it to avoid duplicate/raw output
                    logger.debug("Skipping TaskResult in stream")
                    continue
                
                # Determine message source and content
                source = getattr(message, 'source', 'unknown')
                content = getattr(message, 'content', None)
                
                # Skip messages without proper content
                if content is None or not isinstance(content, str):
                    logger.debug(f"Skipping message without string content: {type(message)}")
                    continue
                
                # Skip empty content
                if not content.strip():
                    continue
                
                # Update agent status
                if source in self._status.agents:
                    agent_status = self._status.agents[source]
                    agent_status.active = True
                    agent_status.message_count += 1
                    agent_status.last_message = content[:200] if content else None
                    
                    # Mark other agents as inactive
                    for name, status in self._status.agents.items():
                        if name != source:
                            status.active = False
                
                # Increment round counter
                round_num += 1
                
                # Log to discussion file
                self._discussion_logger.log_agent_message(
                    agent=source,
                    message=content or "",
                    round_num=round_num,
                )
                
                # Yield agent status update
                yield {
                    "type": "agent_status",
                    "agent": source,
                    "active": True,
                    "message_count": self._status.agents.get(source, AgentStatus(name=source)).message_count,
                }
                
                # Yield the message content
                yield {
                    "type": "agent_message",
                    "agent": source,
                    "content": content,
                }

                # Attempt to derive structured trade info once per run
                if not self._trade_emitted:
                    parsed_trade, parsed_chart = self._parse_trade_recommendation(
                        content,
                        symbols_override or self._extract_symbols(query),
                    )
                    if parsed_trade:
                        self._trade_emitted = True
                        yield {
                            "type": "trade_recommendation",
                            "data": parsed_trade,
                        }
                    if parsed_chart:
                        self._chart_emitted = True
                        yield {
                            "type": "chart_config",
                            "data": parsed_chart,
                        }
                
                # Check for consensus updates
                if self._termination:
                    term_status = self._termination.get_status()
                    if term_status["consensus"]["votes"] > 0:
                        yield {
                            "type": "consensus_update",
                            "consensus": term_status["consensus"],
                        }
            
            # Get final termination status
            term_status = self._termination.get_status() if self._termination else {}
            
            # Log termination
            self._discussion_logger.log_termination(
                reason=term_status.get("termination_reason", "completed"),
                final_consensus=term_status.get("consensus", {}),
            )
            
            # Yield completion
            yield {
                "type": "query_complete",
                "session_id": self._current_session_id,
                "termination": term_status,
            }
            
            logger.info(
                "Agent discussion completed",
                session_id=self._current_session_id,
                termination_reason=term_status.get("termination_reason"),
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Agent discussion failed",
                session_id=self._current_session_id,
                error=error_msg,
            )
            
            if self._discussion_logger:
                self._discussion_logger.log_error(error_msg)
            
            yield {
                "type": "error",
                "error": error_msg,
                "session_id": self._current_session_id,
            }
            
        finally:
            self._status.running = False
            self._status.current_query = None
            
            # Mark all agents as inactive
            for agent_status in self._status.agents.values():
                agent_status.active = False
    
    async def get_agent_statuses(self) -> dict[str, dict]:
        """Get current status of all agents"""
        if not self._status.agents:
            return {}
        
        return {
            name: {
                "active": status.active,
                "message_count": status.message_count,
                "last_message": status.last_message,
            }
            for name, status in self._status.agents.items()
        }
    
    async def shutdown(self) -> None:
        """Shutdown the agent team and cleanup resources"""
        logger.info("Shutting down Trading Agent Team...")
        
        self._status.running = False
        self._status.initialized = False
        self._team = None
        self._agents = {}
        self._model_client = None
        
        logger.info("Trading Agent Team shutdown complete")


# Global team instance
_trading_team: TradingAgentTeam | None = None


def get_trading_team() -> TradingAgentTeam:
    """Get or create the global trading team instance"""
    global _trading_team
    if _trading_team is None:
        _trading_team = TradingAgentTeam()
    return _trading_team


async def initialize_trading_team() -> TradingAgentTeam:
    """Initialize and return the global trading team"""
    team = get_trading_team()
    if not team.is_initialized:
        await team.initialize()
    return team
