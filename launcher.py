import os
import sys
import threading
import time
import django
from django.core.management import call_command
import webview

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Dossier données utilisateur (AppData\Roaming\KhalilGestionPro)
DATA_DIR = os.path.join(os.environ['APPDATA'], 'KhalilGestionPro')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

os.environ['MON_STOCK_DB_PATH'] = os.path.join(DATA_DIR, 'db.sqlite3')

def start_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mon_stock.settings')
    django.setup()
    from django.conf import settings
    if not os.path.exists(settings.DATABASES['default']['NAME']):
        call_command('migrate', '--noinput')
        # Créer un superuser par défaut si besoin (optionnel)
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            print("Superutilisateur créé : admin / admin")
    call_command('runserver', '127.0.0.1:8000', '--noreload')

if __name__ == '__main__':
    t = threading.Thread(target=start_django, daemon=True)
    t.start()
    time.sleep(3)
    webview.create_window("Khalil Gestion Pro", "http://127.0.0.1:8000")
    webview.start()
