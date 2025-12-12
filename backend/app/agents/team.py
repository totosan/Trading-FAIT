"""
Trading-FAIT Agent Team
Magentic-One based multi-agent team for trading analysis
"""

import asyncio
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
        - Crypto pairs: BTC/USDT, ETH/USD (with /)
        - Common crypto: Bitcoin, Ethereum, etc.
        """
        symbols = []
        query_upper = query.upper()
        
        # Known stock tickers to look for
        COMMON_STOCKS = {
            "AAPL": "AAPL", "APPLE": "AAPL",
            "MSFT": "MSFT", "MICROSOFT": "MSFT",
            "GOOGL": "GOOGL", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
            "AMZN": "AMZN", "AMAZON": "AMZN",
            "TSLA": "TSLA", "TESLA": "TSLA",
            "NVDA": "NVDA", "NVIDIA": "NVDA",
            "META": "META", "FACEBOOK": "META",
            "NFLX": "NFLX", "NETFLIX": "NFLX",
        }
        
        # Known crypto to look for
        COMMON_CRYPTO = {
            "BTC": "BTC/USDT", "BITCOIN": "BTC/USDT",
            "ETH": "ETH/USDT", "ETHEREUM": "ETH/USDT",
            "SOL": "SOL/USDT", "SOLANA": "SOL/USDT",
            "XRP": "XRP/USDT", "RIPPLE": "XRP/USDT",
            "ADA": "ADA/USDT", "CARDANO": "ADA/USDT",
            "DOGE": "DOGE/USDT", "DOGECOIN": "DOGE/USDT",
        }
        
        # Check for crypto pairs with /
        crypto_pattern = r'\b([A-Z]{2,5})/([A-Z]{3,4})\b'
        for match in re.finditer(crypto_pattern, query_upper):
            symbols.append(f"{match.group(1)}/{match.group(2)}")
        
        # Check for known names
        for key, symbol in {**COMMON_STOCKS, **COMMON_CRYPTO}.items():
            if key in query_upper and symbol not in symbols:
                symbols.append(symbol)
        
        # Check for standalone tickers (2-5 uppercase letters)
        ticker_pattern = r'\b([A-Z]{2,5})\b'
        for match in re.finditer(ticker_pattern, query_upper):
            ticker = match.group(1)
            # Filter out common words
            if ticker not in ["THE", "AND", "FOR", "BUY", "SELL", "USD", "EUR", "USDT", "WAS", "VON", "DER", "DIE", "DAS", "MIT", "FÜR", "ENDE", "TAG", "KURS"]:
                if ticker in COMMON_STOCKS and COMMON_STOCKS[ticker] not in symbols:
                    symbols.append(COMMON_STOCKS[ticker])
        
        return symbols[:3]  # Limit to 3 symbols
    
    async def _enrich_query_with_market_data(self, query: str) -> str:
        """
        Enrich user query with real-time market data.
        
        Extracts symbols from the query, fetches current market data,
        and prepends it to the query for agent context.
        """
        symbols = self._extract_symbols(query)
        
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
    ) -> AsyncGenerator[dict, None]:
        """
        Run a trading query through the agent team.
        
        Yields status updates and agent messages as they occur.
        
        Args:
            query: The trading query (e.g., "Analyze BTC/USDT")
            session_id: Optional session ID for logging
            
        Yields:
            Dict with message type and content
        """
        if not self.is_initialized:
            await self.initialize()
        
        self._status.running = True
        self._status.current_query = query
        
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
            enriched_query = await self._enrich_query_with_market_data(query)
            logger.info("Query enriched with market data", symbols=self._extract_symbols(query))
            
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
