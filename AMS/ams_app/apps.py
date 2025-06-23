from django.apps import AppConfig
import threading

class AmsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ams_app'
    def ready(self):
        print("📦 [apps.py] ready() called.")
        try:
            from .adminviews import start_rfid_reader
            print("🚀 Starting RFID reader thread...")
            threading.Thread(target=start_rfid_reader, daemon=True).start()
            print("✅ RFID reader thread launched.")
        except Exception as e:
            print(f"❌ Failed to start RFID reader: {e}")
