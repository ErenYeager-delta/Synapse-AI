import os
import django
import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synapse_project.settings')
django.setup()

from chat.mongo_store import mongo_store
from django.contrib.auth.models import User as DjangoUser

def setup_admin():
    print("--- Synapse AI: One-Step Admin Setup ---")
    username = input("Enter new Admin Username: ").strip()
    email    = input("Enter Admin Email: ").strip()
    password = input("Enter Admin Password: ").strip()

    if not username or not password:
        print("Error: Username and Password cannot be empty.")
        return

    print(f"\nCreating Admin: {username}...")

    try:
        # 1. Create in MongoDB + Shadow Sync to SQLite
        # Our modified create_mongo_user already handles the SQLite shadow sync!
        user_id = mongo_store.create_mongo_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        
        print(f"✅ Success! Admin account '{username}' created.")
        print(f"🚀 You can now login at: http://127.0.0.1:8000/admin")
        
    except Exception as e:
        if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
            print(f"❌ Error: Username '{username}' already exists. Please choose a different one.")
        else:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    setup_admin()
