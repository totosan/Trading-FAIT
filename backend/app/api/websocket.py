"""
Trading-FAIT WebSocket API
Real-time communication between frontend and agent team
"""

import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..core.config import get_settings
from ..core.logging import get_logger
from ..agents.team import get_trading_team, TradingAgentTeam
from ..services.market_data import get_market_data_service
from ..services.conversation import get_conversation_manager, ConversationContext

logger = get_logger(__name__)


class WebSocketMessage(BaseModel):
    """Incoming WebSocket message structure"""
    type: str
    message: str | None = None
    symbol: str | None = None
    session_id: str | None = None


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self._settings = get_settings()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and register a new connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}")
        
        # Send connection confirmation
        await self.send_message(client_id, {
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    async def disconnect(self, client_id: str):
        """Remove a connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client disconnected: {client_id}")
    
    async def send_message(self, client_id: str, message: dict):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                await self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)


# Global connection manager
manager = ConnectionManager()


async def handle_query(
    client_id: str,
    query: str,
    session_id: str | None = None,
):
    """
    Handle a trading query from the client.
    
    Supports follow-up conversations with context management:
    - Maintains conversation history per session
    - Detects ambiguous references ("hierzu", "dazu") 
    - Handles quick price queries without full agent discussion
    """
    
    session_id = session_id or str(uuid.uuid4())
    
    # Get conversation context
    conv_manager = get_conversation_manager()
    context = conv_manager.get_or_create(session_id)
    
    # Get the trading team for symbol extraction
    team = get_trading_team()
    
    # Extract symbols from current query
    current_symbols = team._extract_symbols(query)
    
    # Check if this is a follow-up reference without explicit symbol
    needs_clarification, candidates = context.needs_clarification(query)
    
    if needs_clarification and not current_symbols:
        # Ask for clarification
        clarification_msg = f"Gerne! Meinst du {', '.join(candidates[:-1])} oder {candidates[-1]}? Oder alle zusammen?"
        if len(candidates) == 2:
            clarification_msg = f"Gerne! Meinst du {candidates[0]} oder {candidates[1]}? Oder beide?"
        
        await manager.send_message(client_id, {
            "type": "clarification_needed",
            "message": clarification_msg,
            "candidates": candidates,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return
    
    # If no explicit symbol but context has symbols, fallback to last discussed symbol
    if not current_symbols and context.active_symbols:
        # Check for patterns like "..und MSFT?" - implied same type of query
        if query.strip().lower().startswith("..und") or query.strip().lower().startswith("und "):
            # continue (could contain new symbol after und)
            pass
        else:
            # Default: reuse last symbol from context for follow-up questions
            current_symbols = context.get_last_symbols(1)
    
    # Detect if this is a quick price query
    is_price_query = _is_quick_price_query(query)
    is_analysis_request = _is_analysis_request(query)
    
    # Quick price query - bypass full agent discussion
    if is_price_query and current_symbols:
        await _handle_quick_price_query(client_id, session_id, query, current_symbols, context)
        return
    
    # Notify query start
    await manager.send_message(client_id, {
        "type": "query_start",
        "session_id": session_id,
        "query": query,
        "context_symbols": context.active_symbols,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    try:
        # Check if Azure OpenAI is configured
        settings = get_settings()
        if not settings.is_configured:
            await manager.send_message(client_id, {
                "type": "error",
                "error": "Azure OpenAI ist nicht konfiguriert. Bitte .env Datei prüfen.",
                "session_id": session_id,
            })
            return
        
        # Build context for the query
        conversation_context = context.get_context_for_query(query)
        
        # Add user message to context
        context.add_user_message(
            content=query,
            symbols=current_symbols,
            is_price_query=is_price_query,
            is_analysis=is_analysis_request,
        )
        
        # Stream agent responses
        final_content = ""
        async for event in team.run_query(
            query, 
            session_id=session_id,
            conversation_context=conversation_context,
            symbols_override=current_symbols,
        ):
            # Add timestamp to event
            event["timestamp"] = datetime.utcnow().isoformat()
            
            # Capture final content for context
            if event.get("type") == "agent_message":
                final_content = event.get("content", "")
            
            # Send to client
            await manager.send_message(client_id, event)
            
            # Small delay to prevent flooding
            await asyncio.sleep(0.05)
        
        # Add assistant response to context
        if final_content:
            context.add_assistant_message(
                content=final_content,
                symbols=current_symbols,
            )
        
    except Exception as e:
        logger.error(f"Error handling query: {e}")
        await manager.send_message(client_id, {
            "type": "error",
            "error": str(e),
            "session_id": session_id,
        })


def _is_quick_price_query(query: str) -> bool:
    """
    Detect if query is a simple price/quote request.
    
    Examples:
    - "Welchen Preis hat AAPL?"
    - "Was kostet BTC?"
    - "MSFT Kurs"
    - "..und MSFT?"
    """
    query_lower = query.lower()
    
    price_patterns = [
        r'welchen?\s+preis',
        r'was\s+kostet',
        r'aktueller?\s+kurs',
        r'aktueller?\s+preis',
        r'kurs\s+von',
        r'preis\s+von',
        r'^\.{2,}und\s+\w+\??$',  # "..und MSFT?"
        r'^und\s+\w+\??$',  # "und MSFT?"
        r'^\w{2,5}\s+kurs\??$',  # "MSFT Kurs?"
        r'^\w{2,5}\s+preis\??$',  # "AAPL Preis?"
        r'wie\s+steht\s+\w+',
        r'wie\s+ist\s+der\s+kurs',
    ]
    
    return any(re.search(pattern, query_lower) for pattern in price_patterns)


def _is_analysis_request(query: str) -> bool:
    """Detect if query requests an analysis"""
    query_lower = query.lower()
    
    analysis_patterns = [
        r'analy[sz]',
        r'bewert',
        r'einsch[äa]tz',
        r'empfehl',
        r'trade\s*idea',
        r'handels.*empfehlung',
        r'was\s+denkst\s+du',
        r'wie\s+siehst\s+du',
    ]
    
    return any(re.search(pattern, query_lower) for pattern in analysis_patterns)


async def _handle_quick_price_query(
    client_id: str,
    session_id: str,
    query: str,
    symbols: list[str],
    context: ConversationContext,
):
    """
    Handle quick price queries without full agent discussion.
    Much faster and token-efficient.
    """
    market_service = get_market_data_service()
    
    results = []
    for symbol in symbols[:3]:  # Max 3 symbols
        try:
            quote = await market_service.get_quick_quote(symbol)
            
            if quote.get("error"):
                results.append(f"❌ {symbol}: Daten nicht verfügbar")
            else:
                price = quote.get("price")
                change = quote.get("change_24h_pct")
                
                if price:
                    price_str = f"${price:,.2f}"
                    change_str = f"({change:+.2f}%)" if change else ""
                    results.append(f"📊 **{symbol}**: {price_str} {change_str}")
                else:
                    results.append(f"⚠️ {symbol}: Kein Preis verfügbar")
                    
        except Exception as e:
            logger.warning(f"Quick quote failed for {symbol}: {e}")
            results.append(f"⚠️ {symbol}: Fehler beim Abruf")
    
    response_text = "\n".join(results)
    
    # Add to context
    context.add_user_message(query, symbols, is_price_query=True)
    context.add_assistant_message(response_text, symbols)
    
    # Send response
    await manager.send_message(client_id, {
        "type": "quick_response",
        "message": response_text,
        "symbols": symbols,
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
    })



async def handle_quote_request(client_id: str, symbol: str):
    """Handle a quick quote request"""
    try:
        market_service = get_market_data_service()
        quote = await market_service.get_quick_quote(symbol)
        
        await manager.send_message(client_id, {
            "type": "quote",
            "data": quote,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        await manager.send_message(client_id, {
            "type": "error",
            "error": f"Fehler beim Abrufen von {symbol}: {e}",
        })


async def handle_agent_status_request(client_id: str):
    """Send current agent statuses"""
    try:
        team = get_trading_team()
        statuses = await team.get_agent_statuses()
        
        await manager.send_message(client_id, {
            "type": "agent_statuses",
            "agents": statuses,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error getting agent statuses: {e}")


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler"""
    
    client_id = str(uuid.uuid4())
    
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")
                
                logger.debug(f"Received message from {client_id}: {msg_type}")
                
                if msg_type == "query":
                    # Handle trading query
                    query = message.get("message", "")
                    if query:
                        # Run query in background task
                        asyncio.create_task(
                            handle_query(
                                client_id,
                                query,
                                message.get("session_id"),
                            )
                        )
                    else:
                        await manager.send_message(client_id, {
                            "type": "error",
                            "error": "Leere Anfrage",
                        })
                
                elif msg_type == "quote":
                    # Quick quote request
                    symbol = message.get("symbol", "")
                    if symbol:
                        asyncio.create_task(
                            handle_quote_request(client_id, symbol)
                        )
                
                elif msg_type == "agent_status":
                    # Request current agent statuses
                    asyncio.create_task(
                        handle_agent_status_request(client_id)
                    )
                
                elif msg_type == "ping":
                    # Heartbeat
                    await manager.send_message(client_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                
                else:
                    await manager.send_message(client_id, {
                        "type": "error",
                        "error": f"Unbekannter Nachrichtentyp: {msg_type}",
                    })
                    
            except json.JSONDecodeError:
                await manager.send_message(client_id, {
                    "type": "error",
                    "error": "Ungültiges JSON",
                })
                
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await manager.disconnect(client_id)
