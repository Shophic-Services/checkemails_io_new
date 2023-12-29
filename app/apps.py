from django.apps import AppConfig


class AppConfig(AppConfig):
    name = 'app'

    def ready(self):
        _ = self
        import app.signals
