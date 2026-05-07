from django.urls import re_path
from tools.consumers import BulkDashboardConsumer, ScraperDashboardConsumer


websocket_urlpatterns = [
    re_path(r"^ws/bulk-dashboard/$", BulkDashboardConsumer.as_asgi()),
    re_path(r"^ws/scraper-dashboard/$", ScraperDashboardConsumer.as_asgi()),
]
