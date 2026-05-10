from django.urls import re_path
from .consumers import MetricConsumer

websocket_urlpatterns = [
    re_path(r'ws/metrics/$', MetricConsumer.as_asgi()),
]