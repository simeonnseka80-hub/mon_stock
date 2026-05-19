from django.contrib.auth.models import User
import os

# Get credentials from environment variables or use defaults
username = os.getenv('SUPERUSER_USERNAME', 'admin')
email = os.getenv('SUPERUSER_EMAIL', 'admin@example.com')
password = os.getenv('SUPERUSER_PASSWORD', 'admin123')

# Check if superuser already exists
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"✅ Superuser '{username}' created successfully!")
else:
    print(f"ℹ️ Superuser '{username}' already exists!")
