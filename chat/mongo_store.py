"""
MongoDB storage utility for Synapse.
FIX: Lazy initialization — MongoClient connects only on first use,
     not at Django startup. This prevents migrate from crashing.
"""
import datetime
from bson.objectid import ObjectId

_client = None
_db     = None


def _get_db():
    """Return MongoDB database, connecting lazily on first call."""
    global _client, _db
    if _db is not None:
        return _db
    from django.conf import settings
    from pymongo import MongoClient
    uri = getattr(settings, 'MONGO_URI', 'mongodb://localhost:27017/synapse_mongo')
    _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        _db = _client.get_default_database()
    except Exception:
        _db = _client["synapse_mongo"]
    return _db


class MongoStore:

    @property
    def sessions(self):      return _get_db().sessions
    @property
    def messages(self):      return _get_db().messages
    @property
    def user_settings(self): return _get_db().user_settings
    @property
    def user_queries(self):  return _get_db().user_queries
    @property
    def users(self):         return _get_db().users

    def create_session(self, user_id, title="New Chat"):
        result = self.sessions.insert_one({
            "user_id":    user_id,
            "title":      title,
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow(),
            "is_active":  True,
        })
        session_id = str(result.inserted_id)
        self._sync_session(session_id)
        return session_id

    def get_sessions(self, user_id, limit=20):
        docs = self.sessions.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
        return [{"id": str(s["_id"]), "title": s["title"],
                 "created_at": s["created_at"], "updated_at": s["updated_at"]} for s in docs]

    def get_session(self, session_id, user_id):
        try:
            return self.sessions.find_one({"_id": ObjectId(session_id), "user_id": user_id})
        except Exception:
            return None

    def delete_session(self, session_id, user_id):
        try:
            self.sessions.delete_one({"_id": ObjectId(session_id), "user_id": user_id})
            self.messages.delete_many({"session_id": session_id})
            return True
        except Exception:
            return False

    def add_message(self, session_id, role, content):
        self.messages.insert_one({
            "session_id": session_id,
            "role":       role,
            "content":    content,
            "timestamp":  datetime.datetime.utcnow(),
        })
        try:
            self.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"updated_at": datetime.datetime.utcnow()}}
            )
        except Exception:
            pass
        self._sync_message(session_id, role, content)

    def get_messages(self, session_id):
        docs = self.messages.find({"session_id": session_id}).sort("timestamp", 1)
        return [{"role": m["role"], "content": m["content"], "timestamp": m["timestamp"]} for m in docs]

    def update_session_title(self, session_id, title):
        try:
            self.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"title": title}}
            )
        except Exception:
            pass
        self._sync_session(session_id)

    def get_user_settings(self, user_id):
        try:
            s = self.user_settings.find_one({"user_id": user_id})
            if not s:
                return {"user_id": user_id, "preferred_language": "Python", "personal_api_key": ""}
            return s
        except Exception:
            return {"user_id": user_id, "preferred_language": "Python", "personal_api_key": ""}

    def update_user_settings(self, user_id, preferred_language, personal_api_key):
        self.user_settings.update_one(
            {"user_id": user_id},
            {"$set": {
                "preferred_language": preferred_language,
                "personal_api_key":   personal_api_key,
                "updated_at":         datetime.datetime.utcnow(),
            }},
            upsert=True
        )
    def log_query(self, user_id, query):
        """Log every user question globally for analysis."""
        try:
            self.user_queries.insert_one({
                "user_id":   user_id,
                "query":      query,
                "timestamp":  datetime.datetime.utcnow(),
            })
        except Exception:
            pass

    # ── User Management (MongoDB Auth) ────────────────────────
    def get_mongo_user(self, username):
        """Find user by username."""
        try:
            return self.users.find_one({"username": username})
        except Exception:
            return None

    def get_mongo_user_by_id(self, user_id):
        """Find user by ObjectId (string or ObjectId)."""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            return self.users.find_one({"_id": user_id})
        except Exception:
            return None

    def create_mongo_user(self, username, email, password, is_staff=False, is_superuser=False):
        """Create a new user with hashed password in MongoDB & shadow sync to SQLite."""
        from django.contrib.auth.hashers import make_password
        from django.contrib.auth.models import User as DjangoUser
        try:
            user_doc = {
                "username":     username,
                "email":        email,
                "password":     make_password(password),
                "date_joined":  datetime.datetime.utcnow(),
                "last_login":   None,
                "is_active":    True,
                "is_staff":     is_staff,
                "is_superuser": is_superuser,
            }
            result = self.users.insert_one(user_doc)
            user_id = str(result.inserted_id)

            # Shadow sync to SQLite for Django Admin access
            try:
                # Use update_or_create to avoid duplicates if something went wrong
                DjangoUser.objects.update_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "password": user_doc["password"],
                        "is_staff": is_staff, 
                        "is_superuser": is_superuser,
                        "is_active": True
                    }
                )
            except Exception as se:
                print(f"Shadow sync error (User): {se}")

            return user_id
        except Exception as e:
            raise e

    def _sync_session(self, session_id):
        """Internal helper to sync a session metadata to SQLite."""
        from chat.models import ChatSession
        from django.contrib.auth.models import User as DjangoUser
        try:
            s_mongo = self.sessions.find_one({"_id": ObjectId(session_id)})
            if not s_mongo: return
            
            # user_id now stores the username (portable key)
            u_name = s_mongo['user_id']
            u_sql = DjangoUser.objects.get(username=u_name)
            
            ChatSession.objects.update_or_create(
                id=int(str(ObjectId(session_id))[:8], 16) % 2147483647, # Pseudo-ID for SQL
                defaults={
                    "user": u_sql,
                    "title": s_mongo['title'],
                    "is_active": s_mongo['is_active']
                }
            )
        except Exception:
            pass

    def _sync_message(self, session_id, role, content):
        """Internal helper to sync a message to SQLite."""
        from chat.models import ChatSession, ChatMessage
        try:
            # We use a simplified sync for messages to avoid overhead
            # Only sync if the session exists in shadow
            s_id_int = int(str(ObjectId(session_id))[:8], 16) % 2147483647
            s_sql = ChatSession.objects.filter(id=s_id_int).first()
            if s_sql:
                ChatMessage.objects.create(
                    session=s_sql,
                    role=role,
                    content=content
                )
        except Exception:
            pass


mongo_store = MongoStore()   # Safe now — no network call at import time
