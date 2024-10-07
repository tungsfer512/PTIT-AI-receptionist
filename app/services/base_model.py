import json
from fastapi import WebSocket
import os
import httpx

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_response(self, response: dict, websocket: WebSocket):
        message = json.dumps(response)
        await websocket.send_text(message)

    async def broadcast(self, response: dict):
        for connection in self.active_connections:
            await connection.send_text(json.dumps(response))

# Gui tin nhan qua Telegram
class TelegramService:
    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("BOT_TOKEN must be provided")
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, phone_number: str, message: str):
        try:
            chat_id = await self._get_chat_id_by_phone(phone_number)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "Markdown"
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            raise Exception(f"Failed to send Telegram message: {str(e)}")

    # Tim chat_id tu database ( tam thoi fix cung 1 user )
    async def _get_chat_id_by_phone(self, phone_number: str) -> int:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID must be set")
        return chat_id