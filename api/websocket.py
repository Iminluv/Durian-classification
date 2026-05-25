from fastapi import WebSocket, WebSocketDisconnect
import json
from core.logger import logger

class ConnectionManager:
    def __init__(self):
        self.live_connections: list[WebSocket] = []
        self.event_connections: list[WebSocket] = []

    async def connect_live(self, websocket: WebSocket):
        await websocket.accept()
        self.live_connections.append(websocket)
        logger.info(f"New client connected to live MJPEG feed. Total: {len(self.live_connections)}")

    def disconnect_live(self, websocket: WebSocket):
        if websocket in self.live_connections:
            self.live_connections.remove(websocket)
            logger.info(f"Client disconnected from live MJPEG feed. Total: {len(self.live_connections)}")

    async def connect_event(self, websocket: WebSocket):
        await websocket.accept()
        self.event_connections.append(websocket)
        logger.info(f"New client connected to events stream. Total: {len(self.event_connections)}")

    def disconnect_event(self, websocket: WebSocket):
        if websocket in self.event_connections:
            self.event_connections.remove(websocket)
            logger.info(f"Client disconnected from events stream. Total: {len(self.event_connections)}")

    async def broadcast_live(self, base64_image: str):
        """Broadcasts JPEG base64 string to all live feed listeners."""
        for connection in list(self.live_connections):
            try:
                await connection.send_text(base64_image)
            except Exception:
                self.disconnect_live(connection)

    async def broadcast_event(self, event_data: dict):
        """Broadcasts JSON event data to all event listeners."""
        event_str = json.dumps(event_data)
        for connection in list(self.event_connections):
            try:
                await connection.send_text(event_str)
            except Exception:
                self.disconnect_event(connection)

manager = ConnectionManager()
