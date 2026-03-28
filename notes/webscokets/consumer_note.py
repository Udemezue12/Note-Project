import json

from channels.generic.websocket import AsyncWebsocketConsumer


class NoteConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f"user_{self.user.id}"
        # self.group_name = "test_group"

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()
        print("WebSocket CONNECTED:", self.scope["user"])

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def note_update(self, event):
        print("WEBSOCKET EVENT RECEIVED:", event)
        await self.send(text_data=json.dumps(event["data"]))
    async def force_logout(self, event):
        print("FORCE LOGOUT RECEIVED")
        await self.close(code=4003)
