from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BulkDashboardConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        await self.channel_layer.group_add(
            "bulk_dashboard",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            "bulk_dashboard",
            self.channel_name
        )

    async def job_update(self, event):
        dataset = event["data"]
        dataset.update({'credit_balance': event['credit_balance'],
                        'credit_reserved': event['credit_reserved']})
        await self.send_json(dataset)



class ScraperDashboardConsumer(AsyncJsonWebsocketConsumer):
 
    async def connect(self):
        await self.channel_layer.group_add(
            "scraper_dashboard",
            self.channel_name,
        )
        await self.accept()
 
    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            "scraper_dashboard",
            self.channel_name,
        )
 
    async def job_update(self, event):
        """Received from push_scraper_job_update → forward to WebSocket client."""
        payload = event["data"]
        payload.update({'credit_balance': event['credit_balance'],
                        'credit_reserved': event['credit_reserved']})
        await self.send_json(payload)