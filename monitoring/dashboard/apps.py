from django.apps import AppConfig
import threading


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    started = False

    def ready(self):

        if not DashboardConfig.started:

            from .socket_server import start_udp_server

            threading.Thread(
                target=start_udp_server,
                daemon=True
            ).start()

            DashboardConfig.started = True