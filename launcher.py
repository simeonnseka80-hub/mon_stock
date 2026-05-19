import os
import sys

"""
Desktop launcher for Windows only. This module is intentionally safe to import on
non-Windows systems (e.g., Render). The original launcher contained top-level
references to APPDATA and started a GUI which caused failures when imported or
executed in Linux containers. We now only execute desktop code when run on
Windows and when invoked as a script.
"""


def main():
    import threading
    import time
    import django
    from django.core.management import call_command
    try:
        import webview
    except Exception:
        webview = None

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)

    # Use APPDATA only if available
    appdata = os.environ.get('APPDATA')
    DATA_DIR = os.path.join(appdata, 'KhalilGestionPro') if appdata else os.path.join(BASE_DIR, 'data')
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    os.environ['MON_STOCK_DB_PATH'] = os.path.join(DATA_DIR, 'db.sqlite3')

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mon_stock.settings')
    django.setup()
    from django.conf import settings

    db_name = settings.DATABASES['default']['NAME']
    # If the database file does not exist, run migrations and create default superuser
    if isinstance(db_name, str) and not os.path.exists(db_name):
        call_command('migrate', '--noinput')
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            print("Superutilisateur créé : admin / admin")

    # Start local development server (desktop only)
    call_command('runserver', '127.0.0.1:8000', '--noreload')


if __name__ == '__main__':
    # Only run the desktop launcher on Windows
    if os.name == 'nt':
        main()
    else:
        print('launcher.py is desktop-only and will not run on this OS.')
