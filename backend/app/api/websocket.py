"""
Trading-FAIT WebSocket API
Real-time communication between frontend and agent team
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..core.config import get_settings
from ..core.logging import get_logger
from ..agents.team import get_trading_team, TradingAgentTeam
from ..services.market_data import get_market_data_service

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
    """Handle a trading query from the client"""
    
    session_id = session_id or str(uuid.uuid4())
    
    # Notify query start
    await manager.send_message(client_id, {
        "type": "query_start",
        "session_id": session_id,
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    try:
        # Get the trading team
        team = get_trading_team()
        
        # Check if Azure OpenAI is configured
        settings = get_settings()
        if not settings.is_configured:
            await manager.send_message(client_id, {
                "type": "error",
                "error": "Azure OpenAI ist nicht konfiguriert. Bitte .env Datei prüfen.",
                "session_id": session_id,
            })
            return
        
        # Stream agent responses
        async for event in team.run_query(query, session_id=session_id):
            # Add timestamp to event
            event["timestamp"] = datetime.utcnow().isoformat()
            
            # Send to client
            await manager.send_message(client_id, event)
            
            # Small delay to prevent flooding
            await asyncio.sleep(0.05)
        
    except Exception as e:
        logger.error(f"Error handling query: {e}")
        await manager.send_message(client_id, {
            "type": "error",
            "error": str(e),
            "session_id": session_id,
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
