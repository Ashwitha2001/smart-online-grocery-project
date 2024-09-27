# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DeliveryStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'delivery_status'

        # Join group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        delivery_id = data['delivery_id']
        status = data['status']

        # Update the delivery status in the database
        delivery = await Delivery.objects.get(id=delivery_id)
        delivery.status = status
        await database_sync_to_async(delivery.save)()

        # Send message to the group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'delivery_status_update',
                'delivery_id': delivery_id,
                'status': status
            }
        )

    async def delivery_status_update(self, event):
        delivery_id = event['delivery_id']
        status = event['status']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'delivery_id': delivery_id,
            'status': status
        }))
