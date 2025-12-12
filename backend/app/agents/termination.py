"""
Trading-FAIT Termination Conditions
Majority consensus (2/3) and turn-based termination for agent discussions
"""

import re
from dataclasses import dataclass, field
from typing import Sequence

from autogen_agentchat.base import TerminatedException, TerminationCondition
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    StopMessage,
    TextMessage,
    MultiModalMessage,
    HandoffMessage,
    ToolCallSummaryMessage,
)

# Tuple of concrete message types that have 'content' and 'source' attributes
# Used for isinstance() checks since ChatMessage is a Union type alias
_CHAT_MESSAGE_TYPES = (TextMessage, MultiModalMessage, StopMessage, HandoffMessage, ToolCallSummaryMessage)


@dataclass
class ConsensusTracker:
    """Tracks agent consensus during discussions"""
    
    total_agents: int = 6
    consensus_threshold: float = 2/3  # 66.7% majority needed
    
    # Track votes per agent (latest vote wins)
    agent_votes: dict[str, bool] = field(default_factory=dict)
    
    # Consensus patterns to detect in messages
    AGREE_PATTERNS = [
        r"\[CONSENSUS:\s*AGREE\]",
        r"\[AGREE\]",
        r"I agree with (?:the|this) (?:analysis|recommendation)",
        r"I support this (?:trade|recommendation)",
        r"This analysis is sound",
    ]
    
    DISAGREE_PATTERNS = [
        r"\[CONSENSUS:\s*DISAGREE\]",
        r"\[DISAGREE\]",
        r"I disagree with",
        r"I have concerns about",
        r"This analysis (?:is flawed|needs revision)",
    ]
    
    def parse_vote(self, agent_name: str, message: str) -> bool | None:
        """
        Parse a message for consensus signals.
        
        Returns:
            True if AGREE, False if DISAGREE, None if no clear signal
        """
        message_lower = message.lower()
        message_original = message
        
        # Check for explicit agree patterns
        for pattern in self.AGREE_PATTERNS:
            if re.search(pattern, message_original, re.IGNORECASE):
                self.agent_votes[agent_name] = True
                return True
        
        # Check for explicit disagree patterns
        for pattern in self.DISAGREE_PATTERNS:
            if re.search(pattern, message_original, re.IGNORECASE):
                self.agent_votes[agent_name] = False
                return False
        
        return None
    
    def check_consensus(self) -> tuple[bool, dict]:
        """
        Check if consensus has been reached.
        
        Returns:
            Tuple of (consensus_reached, stats_dict)
        """
        if not self.agent_votes:
            return False, {"votes": 0, "agrees": 0, "disagrees": 0, "threshold": self.consensus_threshold}
        
        agrees = sum(1 for v in self.agent_votes.values() if v)
        disagrees = sum(1 for v in self.agent_votes.values() if not v)
        total_votes = len(self.agent_votes)
        
        stats = {
            "votes": total_votes,
            "agrees": agrees,
            "disagrees": disagrees,
            "threshold": self.consensus_threshold,
            "agent_votes": dict(self.agent_votes),
        }
        
        # Need at least 4 votes (2/3 of 6) to have potential consensus
        min_votes_needed = int(self.total_agents * self.consensus_threshold)
        
        # Check if we have enough agrees for consensus
        if agrees >= min_votes_needed:
            stats["consensus_type"] = "AGREE"
            return True, stats
        
        # Check if we have enough disagrees (meaning the proposal is rejected)
        if disagrees >= min_votes_needed:
            stats["consensus_type"] = "DISAGREE"
            return True, stats
        
        return False, stats
    
    def reset(self) -> None:
        """Reset vote tracking for a new proposal"""
        self.agent_votes.clear()


class TradingTerminationCondition(TerminationCondition):
    """
    Custom termination condition for trading agent discussions.
    
    Terminates when:
    1. Majority consensus (2/3 agents agree) is reached
    2. Maximum turns exceeded
    3. Maximum stalls (no progress) exceeded
    4. Stop message received
    """
    
    def __init__(
        self,
        max_turns: int = 20,
        max_stalls: int = 3,
        total_agents: int = 6,
    ):
        self._max_turns = max_turns
        self._max_stalls = max_stalls
        self._turn_count = 0
        self._stall_count = 0
        self._last_message_hash: str | None = None
        self._terminated = False
        self._termination_reason: str | None = None
        
        self.consensus_tracker = ConsensusTracker(total_agents=total_agents)
    
    @property
    def terminated(self) -> bool:
        return self._terminated
    
    async def __call__(
        self, messages: Sequence[AgentEvent | ChatMessage]
    ) -> StopMessage | None:
        """
        Check if the conversation should terminate.
        
        Args:
            messages: Sequence of messages in the conversation
            
        Returns:
            StopMessage if should terminate, None otherwise
        """
        if self._terminated:
            raise TerminatedException("Conversation already terminated")
        
        if not messages:
            return None
        
        # Get the latest message
        last_message = messages[-1]
        
        # Check if it's already a stop message
        if isinstance(last_message, StopMessage):
            self._terminated = True
            self._termination_reason = "Stop message received"
            return last_message
        
        # Increment turn count
        self._turn_count += 1
        
        # Check for stalls (repeated similar messages)
        # Use concrete message types tuple since ChatMessage is a Union type alias
        if isinstance(last_message, _CHAT_MESSAGE_TYPES):
            current_hash = hash(last_message.content[:100] if last_message.content else "")
            if current_hash == self._last_message_hash:
                self._stall_count += 1
            else:
                self._stall_count = 0
            self._last_message_hash = current_hash
            
            # Parse for consensus signals
            if hasattr(last_message, 'source') and last_message.content:
                self.consensus_tracker.parse_vote(
                    last_message.source,
                    last_message.content
                )
        
        # Check termination conditions
        
        # 1. Check for consensus
        consensus_reached, stats = self.consensus_tracker.check_consensus()
        if consensus_reached:
            self._terminated = True
            consensus_type = stats.get("consensus_type", "UNKNOWN")
            self._termination_reason = f"Consensus reached: {consensus_type} ({stats['agrees']}/{stats['votes']} agents)"
            return StopMessage(
                content=f"Discussion terminated: {self._termination_reason}",
                source="TradingTerminationCondition",
            )
        
        # 2. Check max turns
        if self._turn_count >= self._max_turns:
            self._terminated = True
            self._termination_reason = f"Maximum turns ({self._max_turns}) reached"
            return StopMessage(
                content=f"Discussion terminated: {self._termination_reason}",
                source="TradingTerminationCondition",
            )
        
        # 3. Check max stalls
        if self._stall_count >= self._max_stalls:
            self._terminated = True
            self._termination_reason = f"Maximum stalls ({self._max_stalls}) reached - no progress"
            return StopMessage(
                content=f"Discussion terminated: {self._termination_reason}",
                source="TradingTerminationCondition",
            )
        
        return None
    
    async def reset(self) -> None:
        """Reset the termination condition for a new conversation"""
        self._turn_count = 0
        self._stall_count = 0
        self._last_message_hash = None
        self._terminated = False
        self._termination_reason = None
        self.consensus_tracker.reset()
    
    def get_status(self) -> dict:
        """Get current termination condition status"""
        consensus_reached, consensus_stats = self.consensus_tracker.check_consensus()
        return {
            "turn_count": self._turn_count,
            "max_turns": self._max_turns,
            "stall_count": self._stall_count,
            "max_stalls": self._max_stalls,
            "terminated": self._terminated,
            "termination_reason": self._termination_reason,
            "consensus": consensus_stats,
        }


class MaxTurnsTermination(TerminationCondition):
    """Simple max turns termination for testing"""
    
    def __init__(self, max_turns: int = 10):
        self._max_turns = max_turns
        self._turn_count = 0
        self._terminated = False
    
    @property
    def terminated(self) -> bool:
        return self._terminated
    
    async def __call__(
        self, messages: Sequence[AgentEvent | ChatMessage]
    ) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Already terminated")
        
        self._turn_count += 1
        
        if self._turn_count >= self._max_turns:
            self._terminated = True
            return StopMessage(
                content=f"Max turns ({self._max_turns}) reached",
                source="MaxTurnsTermination",
            )
        
        return None
    
    async def reset(self) -> None:
        self._turn_count = 0
        self._terminated = False
