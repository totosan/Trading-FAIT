"""Trading-FAIT Agents Package - Magentic-One Trading Team"""

from .prompts import AGENT_PROMPTS, AGENT_DESCRIPTIONS
from .termination import TradingTerminationCondition, ConsensusTracker
from .team import (
    TradingAgentTeam,
    AgentStatus,
    TeamStatus,
    get_trading_team,
    initialize_trading_team,
)

__all__ = [
    # Prompts
    "AGENT_PROMPTS",
    "AGENT_DESCRIPTIONS",
    # Termination
    "TradingTerminationCondition",
    "ConsensusTracker",
    # Team
    "TradingAgentTeam",
    "AgentStatus",
    "TeamStatus",
    "get_trading_team",
    "initialize_trading_team",
]
