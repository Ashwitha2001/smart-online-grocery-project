from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/delivery-status/', consumers.DeliveryStatusConsumer.as_asgi()),
]
