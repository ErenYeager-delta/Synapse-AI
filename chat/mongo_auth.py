"""
Custom MongoDB Authentication Backend for Django.
Mimics Django's User model for compatibility with login(), authenticate(), etc.
"""
from django.contrib.auth.hashers import check_password
from .mongo_store import mongo_store

class MongoAuthBackend:
    """Authenticates against MongoDB 'users' collection with SQLite fallback support."""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        
        try:
            # Check MongoDB first
            user_doc = mongo_store.get_mongo_user(username)
            if user_doc and check_password(password, user_doc["password"]):
                # --- Shadow Recovery ---
                # Ensure the shadow user exists in SQL and matches Mongo status
                from django.contrib.auth.models import User as DjangoUser
                user, created = DjangoUser.objects.update_or_create(
                    username=username,
                    defaults={
                        "password":     user_doc["password"],
                        "email":        user_doc.get("email", ""),
                        "is_staff":     user_doc.get("is_staff", False),
                        "is_superuser": user_doc.get("is_superuser", False),
                        "is_active":    True
                    }
                )
                return user
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Mongo Auth Error: {e}")
            
        return None

    def get_user(self, user_id):
        """Standard Django User loader."""
        from django.contrib.auth.models import User as DjangoUser
        try:
            return DjangoUser.objects.get(pk=user_id)
        except DjangoUser.DoesNotExist:
            return None
