from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .mongo_store import mongo_store
import datetime

@receiver(post_save, sender=User)
def sync_user_to_mongo(sender, instance, created, **kwargs):
    """
    Automatically syncs a Django User (from SQLite) to MongoDB.
    This enables 'python manage.py createsuperuser' to work across both databases.
    """
    try:
        # Prepare the user document for MongoDB
        user_doc = {
            "username":     instance.username,
            "email":        instance.email,
            "password":     instance.password, # Already hashed if created via Django
            "is_active":    instance.is_active,
            "is_staff":     instance.is_staff,
            "is_superuser": instance.is_superuser,
            "date_joined":  instance.date_joined if instance.date_joined else datetime.datetime.utcnow(),
            "last_login":   instance.last_login,
        }
        
        # Use upsert (Update if exists, Insert if not) in MongoDB
        mongo_store.users.update_one(
            {"username": instance.username},
            {"$set": user_doc},
            upsert=True
        )
    except Exception as e:
        # Non-blocking error for main Django process
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Signal Sync Error (MongoDB): {e}")
