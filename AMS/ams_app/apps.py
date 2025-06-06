from django.apps import AppConfig
import threading

# This file is part of the AMS project, which is licensed under the GNU General Public License v3.0.
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
