from django.urls import path
from .views import index, history

urlpatterns = [
    path('', index),
    path('history/<str:device_id>/', history),
]