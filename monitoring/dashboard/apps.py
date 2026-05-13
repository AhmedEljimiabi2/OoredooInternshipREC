from django.apps import AppConfig
import threading
import os


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    started = False

    def ready(self):

        # Prevent double-start from Django autoreloader
        if os.environ.get('RUN_MAIN') != 'true':
            return

        if not DashboardConfig.started:

            from .socket_server import start_udp_server

            threading.Thread(
                target=start_udp_server,
                daemon=True
            ).start()

            DashboardConfig.started = True