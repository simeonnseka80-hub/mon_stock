import os
import django

# Initialiser l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mon_stock.settings')
django.setup()

from django.contrib.auth.models import User

username = os.getenv('SUPERUSER_USERNAME', 'admin')
email = os.getenv('SUPERUSER_EMAIL', 'admin@example.com')
password = os.getenv('SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"✅ Superuser '{username}' created successfully!")
else:
    print(f"ℹ️  Superuser '{username}' already exists!")
