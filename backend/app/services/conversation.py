"""
Trading-FAIT Conversation Context Management
Manages conversation history with token-efficient summarization for follow-up queries.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import re


@dataclass
class ConversationTurn:
    """A single turn in the conversation"""
    role: str  # "user" or "assistant"
    content: str
    symbols: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_price_query: bool = False
    is_analysis: bool = False


@dataclass
class ConversationContext:
    """
    Token-efficient conversation context.
    
    Maintains:
    - Recent symbols discussed (for "...und MSFT?" type queries)
    - Compressed history summary (not full messages)
    - Last N turns for immediate context
    """
    session_id: str
    
    # Active symbols from conversation (max 5)
    active_symbols: list[str] = field(default_factory=list)
    
    # Last few turns (compressed, max 5)
    recent_turns: list[ConversationTurn] = field(default_factory=list)
    
    # Running summary of conversation (very compressed)
    summary: str = ""
    
    # Created timestamp
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Constants
    MAX_RECENT_TURNS: int = 5
    MAX_ACTIVE_SYMBOLS: int = 5
    MAX_SUMMARY_LENGTH: int = 500
    
    def add_user_message(
        self, 
        content: str, 
        symbols: list[str] | None = None,
        is_price_query: bool = False,
        is_analysis: bool = False,
    ) -> None:
        """Add a user message to the context"""
        turn = ConversationTurn(
            role="user",
            content=self._compress_content(content),
            symbols=symbols or [],
            is_price_query=is_price_query,
            is_analysis=is_analysis,
        )
        self._add_turn(turn)
        
        # Update active symbols
        if symbols:
            for symbol in symbols:
                if symbol not in self.active_symbols:
                    self.active_symbols.insert(0, symbol)
            # Keep only most recent symbols
            self.active_symbols = self.active_symbols[:self.MAX_ACTIVE_SYMBOLS]
    
    def add_assistant_message(
        self, 
        content: str, 
        symbols: list[str] | None = None,
    ) -> None:
        """Add an assistant response to the context"""
        turn = ConversationTurn(
            role="assistant",
            content=self._compress_content(content),
            symbols=symbols or [],
        )
        self._add_turn(turn)
    
    def _add_turn(self, turn: ConversationTurn) -> None:
        """Add a turn and maintain limits"""
        self.recent_turns.append(turn)
        
        # If exceeding max turns, summarize oldest and remove
        while len(self.recent_turns) > self.MAX_RECENT_TURNS:
            oldest = self.recent_turns.pop(0)
            self._update_summary(oldest)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def _compress_content(self, content: str) -> str:
        """Compress content to essential information"""
        # Remove markdown formatting
        content = re.sub(r'#{1,6}\s+', '', content)
        content = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', content)
        
        # Keep only first 200 chars for context
        if len(content) > 200:
            content = content[:200] + "..."
        
        return content.strip()
    
    def _update_summary(self, old_turn: ConversationTurn) -> None:
        """Update running summary with evicted turn"""
        # Create minimal summary entry
        if old_turn.symbols:
            symbol_str = ", ".join(old_turn.symbols)
            if old_turn.role == "user":
                if old_turn.is_price_query:
                    entry = f"Preisabfrage: {symbol_str}"
                elif old_turn.is_analysis:
                    entry = f"Analyse angefragt: {symbol_str}"
                else:
                    entry = f"Diskutiert: {symbol_str}"
            else:
                entry = f"Info zu: {symbol_str}"
            
            if self.summary:
                self.summary += f"; {entry}"
            else:
                self.summary = entry
        
        # Truncate summary if too long
        if len(self.summary) > self.MAX_SUMMARY_LENGTH:
            # Keep most recent part
            self.summary = "..." + self.summary[-(self.MAX_SUMMARY_LENGTH - 3):]
    
    def get_context_for_query(self, current_query: str) -> str:
        """
        Generate context string for the current query.
        Returns a compact context that won't stress token limits.
        """
        if not self.recent_turns and not self.summary:
            return ""
        
        parts = []
        
        # Add summary if exists
        if self.summary:
            parts.append(f"[Vorherige Diskussion: {self.summary}]")
        
        # Add active symbols
        if self.active_symbols:
            parts.append(f"[Aktive Symbole: {', '.join(self.active_symbols)}]")
        
        # Add recent turns (very compressed)
        if self.recent_turns:
            recent_parts = []
            for turn in self.recent_turns[-3:]:  # Only last 3 for context
                role_prefix = "U" if turn.role == "user" else "A"
                # Very short version
                short_content = turn.content[:80] + "..." if len(turn.content) > 80 else turn.content
                recent_parts.append(f"{role_prefix}: {short_content}")
            
            if recent_parts:
                parts.append("[Letzte Nachrichten:\n" + "\n".join(recent_parts) + "]")
        
        return "\n".join(parts)
    
    def get_last_symbols(self, count: int = 2) -> list[str]:
        """Get the last N discussed symbols"""
        return self.active_symbols[:count]
    
    def needs_clarification(self, query: str) -> tuple[bool, list[str]]:
        """
        Check if query needs clarification about which symbol.
        Returns (needs_clarification, candidate_symbols)
        
        E.g., "mache mir hierzu eine Analyse!" with multiple active symbols
        """
        # Patterns that suggest reference to previous context
        reference_patterns = [
            r'\bhierzu\b', r'\bdazu\b', r'\bdavon\b', 
            r'\bhiervon\b', r'\bdieser?\b', r'\bdiese[rsmn]?\b',
            r'\bbeide[rsmn]?\b', r'\ball(?:e[rsmn]?)?\b',
            r'^\.{2,}und\b',  # "..und" pattern
        ]
        
        has_reference = any(
            re.search(pattern, query.lower()) 
            for pattern in reference_patterns
        )
        
        if not has_reference:
            return False, []
        
        # If referencing previous context and multiple symbols active
        if len(self.active_symbols) > 1:
            return True, self.active_symbols[:3]
        
        return False, []


class ConversationManager:
    """
    Manages conversation contexts for multiple sessions.
    Token-efficient design to prevent context window stress.
    """
    
    def __init__(self, max_sessions: int = 100):
        self._sessions: dict[str, ConversationContext] = {}
        self._max_sessions = max_sessions
    
    def get_or_create(self, session_id: str) -> ConversationContext:
        """Get existing context or create new one"""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationContext(session_id=session_id)
            self._cleanup_old_sessions()
        return self._sessions[session_id]
    
    def get(self, session_id: str) -> Optional[ConversationContext]:
        """Get context if exists"""
        return self._sessions.get(session_id)
    
    def _cleanup_old_sessions(self) -> None:
        """Remove oldest sessions if exceeding limit"""
        if len(self._sessions) <= self._max_sessions:
            return
        
        # Sort by updated_at and remove oldest
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda x: x[1].updated_at,
        )
        
        # Remove oldest until under limit
        while len(self._sessions) > self._max_sessions:
            oldest_id = sorted_sessions.pop(0)[0]
            del self._sessions[oldest_id]
    
    def clear_session(self, session_id: str) -> None:
        """Clear a specific session"""
        if session_id in self._sessions:
            del self._sessions[session_id]


# Global conversation manager instance
_conversation_manager: ConversationManager | None = None


def get_conversation_manager() -> ConversationManager:
    """Get or create global conversation manager"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
