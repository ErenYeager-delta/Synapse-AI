import os
import django
import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synapse_project.settings')
django.setup()

from django.contrib.auth.models import User as DjangoUser
from chat.mongo_store import mongo_store

def mass_sync():
    print("--- Synapse AI: Mass Sync Users ---")
    sql_users = DjangoUser.objects.all()
    print(f"Found {sql_users.count()} users in SQLite.")
    
    for u in sql_users:
        print(f"Syncing: {u.username}...")
        user_doc = {
            "username":     u.username,
            "email":        u.email,
            "password":     u.password,
            "is_active":    u.is_active,
            "is_staff":     u.is_staff,
            "is_superuser": u.is_superuser,
            "date_joined":  u.date_joined if u.date_joined else datetime.datetime.utcnow(),
            "last_login":   u.last_login,
        }
        mongo_store.users.update_one(
            {"username": u.username},
            {"$set": user_doc},
            upsert=True
        )
    print("✅ Mass Sync Complete.")

if __name__ == "__main__":
    mass_sync()
