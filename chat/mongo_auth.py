"""
Custom MongoDB Authentication Backend for Django.
Mimics Django's User model for compatibility with login(), authenticate(), etc.
"""
from django.contrib.auth.hashers import check_password
from .mongo_store import mongo_store

class MongoUser:
    """A minimal user object that Django's auth system understands."""
    def __init__(self, user_doc):
        self.id = str(user_doc["_id"])
        self.username = user_doc["username"]
        self.email = user_doc.get("email", "")
        self.is_active = user_doc.get("is_active", True)
        self.is_staff = user_doc.get("is_staff", False)
        self.is_superuser = user_doc.get("is_superuser", False)
        self.is_authenticated = True
        self.is_anonymous = False

    def get_username(self):
        return self.username

    def __str__(self):
        return self.username

    # Admin compatibility methods
    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser or self.is_staff

    def get_all_permissions(self, obj=None):
        return set()

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
                # If valid in Mongo but missing in SQL (common after deployment), restore it
                from django.contrib.auth.models import User as DjangoUser
                if not DjangoUser.objects.filter(username=username).exists():
                    DjangoUser.objects.create(
                        username=username,
                        password=user_doc["password"],
                        email=user_doc.get("email", ""),
                        is_staff=user_doc.get("is_staff", False),
                        is_superuser=user_doc.get("is_superuser", False),
                        is_active=True
                    )
                return MongoUser(user_doc)
        except Exception as e:
            # If MongoDB connection fails, return None so ModelBackend (SQL) can try
            import logging
            logging.getLogger(__name__).warning(f"Mongo Auth Error: {e}")
            
        return None

    def get_user(self, user_id):
        """Rebuild MongoUser object. If user_id is an Int, it belongs to SQLite."""
        # 1. If it's a numeric ID, it's definitely a SQLite user
        try:
            if isinstance(user_id, (int, float)):
                return None # Falls back to ModelBackend (SQL)
            
            # 2. Try MongoDB
            user_doc = mongo_store.get_mongo_user_by_id(user_id)
            if user_doc:
                return MongoUser(user_doc)
        except Exception:
            pass
        return None
