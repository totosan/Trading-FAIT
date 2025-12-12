"""
Trading-FAIT Logging
Structured logging with structlog for agent discussions
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import get_settings


def ensure_log_directory() -> Path:
    """Ensure log directory exists and return path"""
    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def add_timestamp(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add ISO timestamp to log events"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_service_info(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add service information to log events"""
    settings = get_settings()
    event_dict["service"] = settings.app_name
    event_dict["version"] = settings.app_version
    return event_dict


class DiscussionFileLogger:
    """
    Logger for agent discussions that writes to JSON files.
    Each discussion session gets its own file.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.log_dir = ensure_log_directory()
        self.log_file = self.log_dir / f"discussion_{session_id}.json"
        self.messages: list[dict] = []
        self._initialize_file()

    def _initialize_file(self):
        """Initialize the log file with metadata"""
        metadata = {
            "session_id": self.session_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "messages": [],
        }
        self._write_file(metadata)

    def _write_file(self, data: dict):
        """Write data to log file"""
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _read_file(self) -> dict:
        """Read current log file"""
        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"session_id": self.session_id, "messages": []}

    def log_agent_message(
        self,
        agent: str,
        message: str,
        round_num: int,
        metadata: dict | None = None,
    ):
        """Log an agent message to the discussion file"""
        data = self._read_file()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent": agent,
            "round": round_num,
            "message": message[:2000],  # Truncate long messages
        }
        
        if metadata:
            log_entry["metadata"] = metadata
            
        data["messages"].append(log_entry)
        self._write_file(data)

    def log_consensus(self, topic: str, agents: list[str]):
        """Log when consensus is reached"""
        data = self._read_file()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "consensus_reached",
            "topic": topic,
            "agents": agents,
        }
        
        data["messages"].append(log_entry)
        self._write_file(data)

    def log_termination(
        self,
        reason: str,
        total_rounds: int | None = None,
        final_consensus: dict | None = None,
    ):
        """Log discussion termination"""
        data = self._read_file()
        
        data["ended_at"] = datetime.utcnow().isoformat() + "Z"
        data["termination_reason"] = reason
        
        if total_rounds is not None:
            data["total_rounds"] = total_rounds
        if final_consensus is not None:
            data["final_consensus"] = final_consensus
        
        self._write_file(data)

    def log_error(self, error: str, context: dict | None = None):
        """Log an error during discussion"""
        data = self._read_file()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "error",
            "error": error,
        }
        
        if context:
            log_entry["context"] = context
            
        data["messages"].append(log_entry)
        self._write_file(data)


def configure_logging():
    """Configure structlog for the application"""
    settings = get_settings()
    
    # Ensure log directory exists
    ensure_log_directory()
    
    # Shared processors for all loggers
    shared_processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        add_timestamp,
        add_service_info,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()


# Global logger instance
logger = configure_logging()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get the configured logger, optionally bound to a name"""
    if name:
        return logger.bind(logger_name=name)
    return logger


def create_discussion_logger(session_id: str) -> DiscussionFileLogger:
    """Create a new discussion logger for a session"""
    return DiscussionFileLogger(session_id)
