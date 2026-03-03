import os
import django
import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synapse_project.settings')
django.setup()

from chat.mongo_store import mongo_store
from django.contrib.auth.models import User as DjangoUser

username = "vignesh"

print(f"Promoting user: {username}")

# Update MongoDB
res = mongo_store.users.update_one(
    {"username": username},
    {"$set": {
        "is_staff": True, 
        "is_superuser": True,
        "is_active": True
    }}
)

if res.matched_count > 0:
    print("MongoDB record updated.")
    # Update SQLite shadow
    user_doc = mongo_store.get_mongo_user(username)
    if user_doc:
        DjangoUser.objects.update_or_create(
            username=username,
            defaults={
                "email": user_doc.get("email", ""),
                "password": user_doc["password"],
                "is_staff": True,
                "is_superuser": True,
                "is_active": True
            }
        )
        print(f"SQLite shadow updated. {username} is now a superuser.")
else:
    print(f"User {username} not found in MongoDB.")
