"""
MongoDB storage utility for Synapse.

Lazy initialization — MongoClient connects only on first use,
not at Django startup. This prevents migrate from crashing.

Includes connection pooling, index creation, structured logging,
and proper error handling for all MongoDB operations.
"""
import datetime
import logging

import pymongo
import pymongo.errors
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

_client = None
_db = None
_indexes_created = False


def _get_db():
    """Return MongoDB database, connecting lazily on first call.

    Configures the MongoClient with connection pooling (maxPoolSize=50),
    server selection timeout (5 s), and connect timeout (5 s).
    On first successful connection, background indexes are created for
    sessions, messages, user_settings, and users collections.

    Returns:
        pymongo.database.Database: The Synapse MongoDB database handle.
    """
    global _client, _db, _indexes_created
    if _db is not None:
        return _db

    from django.conf import settings
    from pymongo import MongoClient

    uri = getattr(settings, "MONGO_URI", "mongodb://localhost:27017/synapse_mongo")
    _client = MongoClient(
        uri,
        maxPoolSize=50,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    try:
        _db = _client.get_default_database()
    except Exception:
        _db = _client["synapse_mongo"]

    # Create indexes once on first connection
    if not _indexes_created:
        try:
            _db.sessions.create_index(
                [("user_id", 1), ("created_at", -1)], background=True
            )
            _db.messages.create_index(
                [("session_id", 1), ("timestamp", 1)], background=True
            )
            _db.user_settings.create_index("user_id", unique=True, background=True)
            _db.users.create_index("email", unique=True, background=True)
            _db.users.create_index("username", unique=True, background=True)
            _indexes_created = True
            logger.info("MongoDB indexes created successfully.")
        except pymongo.errors.PyMongoError as exc:
            logger.warning("Failed to create MongoDB indexes: %s", exc)

    return _db


def health_check():
    """Ping MongoDB to verify the connection is alive.

    Returns:
        dict: ``{"status": "ok"}`` on success, or
              ``{"status": "error", "detail": "<message>"}`` on failure.
    """
    try:
        db = _get_db()
        db.command("ping")
        return {"status": "ok"}
    except pymongo.errors.PyMongoError as exc:
        logger.error("MongoDB health-check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


def _dt_to_iso(value):
    """Convert a datetime to ISO string, or return str(value) as fallback."""
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    return str(value) if value is not None else None


class MongoStore:
    """High-level wrapper around the Synapse MongoDB collections."""

    @property
    def sessions(self):
        """Return the *sessions* collection handle."""
        return _get_db().sessions

    @property
    def messages(self):
        """Return the *messages* collection handle."""
        return _get_db().messages

    @property
    def user_settings(self):
        """Return the *user_settings* collection handle."""
        return _get_db().user_settings

    @property
    def users(self):
        """Return the *users* collection handle."""
        return _get_db().users

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def create_user(self, username, email, password_hash):
        """Create a new user document in the *users* collection.

        Args:
            username: Unique username string.
            email: Unique email address string.
            password_hash: Pre-hashed password string.

        Returns:
            str: The ``_id`` of the newly inserted user document,
                 or ``None`` if the insert failed (e.g. duplicate key).
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            result = self.users.insert_one({
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "created_at": now,
                "is_active": True,
                "daily_chat_count": 0,
                "daily_chat_reset_date": now.date().isoformat(),
                "total_chats": 0,
                "api_key_preference": None,
            })
            return str(result.inserted_id)
        except pymongo.errors.PyMongoError as exc:
            logger.error("create_user failed for email %s: %s", email, exc)
            return None

    def get_user_by_email(self, email):
        """Find a user document by email address.

        Args:
            email: The email address to search for.

        Returns:
            dict or None: User document with ``id``, ``username``, ``email``,
                ``password_hash``, ``created_at`` (ISO string), ``is_active``,
                ``daily_chat_count``, ``total_chats``, and
                ``api_key_preference``; or ``None`` if not found.
        """
        try:
            doc = self.users.find_one(
                {"email": email},
                projection={
                    "_id": 1, "username": 1, "email": 1, "password_hash": 1,
                    "created_at": 1, "is_active": 1, "daily_chat_count": 1,
                    "total_chats": 1, "api_key_preference": 1,
                },
            )
            if not doc:
                return None
            doc["id"] = str(doc.pop("_id"))
            doc["created_at"] = _dt_to_iso(doc.get("created_at"))
            return doc
        except pymongo.errors.PyMongoError as exc:
            logger.error("get_user_by_email failed for %s: %s", email, exc)
            return None

    def get_user_by_username(self, username):
        """Find a user document by username.

        Args:
            username: The username to search for.

        Returns:
            dict or None: User document with ``id``, ``username``, ``email``,
                ``password_hash``, ``created_at`` (ISO string), ``is_active``,
                ``daily_chat_count``, ``total_chats``, and
                ``api_key_preference``; or ``None`` if not found.
        """
        try:
            doc = self.users.find_one(
                {"username": username},
                projection={
                    "_id": 1, "username": 1, "email": 1, "password_hash": 1,
                    "created_at": 1, "is_active": 1, "daily_chat_count": 1,
                    "total_chats": 1, "api_key_preference": 1,
                },
            )
            if not doc:
                return None
            doc["id"] = str(doc.pop("_id"))
            doc["created_at"] = _dt_to_iso(doc.get("created_at"))
            return doc
        except pymongo.errors.PyMongoError as exc:
            logger.error("get_user_by_username failed for %s: %s", username, exc)
            return None

    def update_user(self, user_id, update_fields):
        """Update arbitrary fields on a user document.

        Args:
            user_id: The ``_id`` of the user (string).
            update_fields: Dictionary of fields to set.

        Returns:
            bool: ``True`` if a document was matched and updated,
                  ``False`` otherwise.
        """
        try:
            update_fields["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_fields},
            )
            return result.matched_count > 0
        except pymongo.errors.PyMongoError as exc:
            logger.error("update_user failed for user %s: %s", user_id, exc)
            return False

    def delete_user(self, user_id):
        """Soft-delete a user by setting ``is_active`` to ``False``.

        Args:
            user_id: The ``_id`` of the user (string).

        Returns:
            bool: ``True`` if the user was deactivated, ``False`` otherwise.
        """
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "is_active": False,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }},
            )
            return result.matched_count > 0
        except pymongo.errors.PyMongoError as exc:
            logger.error("delete_user failed for user %s: %s", user_id, exc)
            return False

    # ------------------------------------------------------------------
    # Chat limits per user
    # ------------------------------------------------------------------

    def check_and_increment_chat_count(self, user_id, daily_limit=50):
        """Check whether the user is within their daily chat limit and increment.

        If the current date (UTC) differs from the stored ``daily_chat_reset_date``,
        the counter is reset to 0 before checking. If the user is within the
        limit, ``daily_chat_count`` and ``total_chats`` are incremented atomically.

        Args:
            user_id: The ``_id`` of the user (string).
            daily_limit: Maximum chats allowed per day (default 50).

        Returns:
            tuple[bool, int]: ``(allowed, remaining)`` where *allowed* is
                ``True`` if the chat is permitted and *remaining* is the
                number of chats left after this one. Returns ``(False, 0)``
                if the limit is reached or on error.
        """
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            today_str = now.date().isoformat()

            doc = self.users.find_one(
                {"_id": ObjectId(user_id)},
                projection={
                    "_id": 1, "daily_chat_count": 1,
                    "daily_chat_reset_date": 1, "total_chats": 1,
                },
            )
            if not doc:
                logger.error("check_and_increment_chat_count: user %s not found", user_id)
                return (False, 0)

            stored_date = doc.get("daily_chat_reset_date", "")
            daily_count = doc.get("daily_chat_count", 0)

            # Reset counter if it's a new day
            if stored_date != today_str:
                daily_count = 0
                self.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {
                        "daily_chat_count": 0,
                        "daily_chat_reset_date": today_str,
                    }},
                )

            if daily_count >= daily_limit:
                return (False, 0)

            # Increment both counters atomically
            self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$inc": {"daily_chat_count": 1, "total_chats": 1},
                    "$set": {"daily_chat_reset_date": today_str},
                },
            )
            remaining = daily_limit - (daily_count + 1)
            return (True, remaining)
        except pymongo.errors.PyMongoError as exc:
            logger.error("check_and_increment_chat_count failed for user %s: %s", user_id, exc)
            return (False, 0)

    def get_user_chat_stats(self, user_id):
        """Return chat usage statistics for a user.

        Args:
            user_id: The ``_id`` of the user (string).

        Returns:
            dict: Contains ``daily_count``, ``daily_limit`` (default 50),
                ``total_chats``, and ``reset_date`` (ISO date string).
                Returns ``None`` on error or if the user is not found.
        """
        try:
            doc = self.users.find_one(
                {"_id": ObjectId(user_id)},
                projection={
                    "_id": 0, "daily_chat_count": 1,
                    "daily_chat_reset_date": 1, "total_chats": 1,
                },
            )
            if not doc:
                return None
            return {
                "daily_count": doc.get("daily_chat_count", 0),
                "daily_limit": 50,
                "total_chats": doc.get("total_chats", 0),
                "reset_date": doc.get("daily_chat_reset_date", ""),
            }
        except pymongo.errors.PyMongoError as exc:
            logger.error("get_user_chat_stats failed for user %s: %s", user_id, exc)
            return None

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, user_id, title="New Chat"):
        """Create a new chat session for *user_id*.

        Args:
            user_id: Identifier of the owning user.
            title: Display title for the session (default ``"New Chat"``).

        Returns:
            str: The ``_id`` of the newly inserted session document,
                 or ``None`` if the insert failed.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            result = self.sessions.insert_one({
                "user_id": user_id,
                "title": title,
                "created_at": now,
                "updated_at": now,
                "is_active": True,
            })
            return str(result.inserted_id)
        except pymongo.errors.PyMongoError as exc:
            logger.error("create_session failed for user %s: %s", user_id, exc)
            return None

    def get_sessions(self, user_id, limit=20):
        """Return the most recent sessions for *user_id*.

        Args:
            user_id: Identifier of the owning user.
            limit: Maximum number of sessions to return (default 20).

        Returns:
            list[dict]: Each dict contains ``id``, ``title``,
                        ``created_at`` (ISO string), and
                        ``updated_at`` (ISO string).
        """
        try:
            docs = (
                self.sessions.find(
                    {"user_id": user_id},
                    projection={"_id": 1, "title": 1, "created_at": 1, "updated_at": 1},
                )
                .sort("updated_at", -1)
                .limit(limit)
            )
            results = []
            for s in docs:
                created = s.get("created_at")
                updated = s.get("updated_at")
                results.append({
                    "id": str(s["_id"]),
                    "title": s.get("title", ""),
                    "created_at": created.isoformat() if isinstance(created, datetime.datetime) else str(created),
                    "updated_at": updated.isoformat() if isinstance(updated, datetime.datetime) else str(updated),
                })
            return results
        except pymongo.errors.PyMongoError as exc:
            logger.error("get_sessions failed for user %s: %s", user_id, exc)
            return []

    def get_session(self, session_id, user_id):
        """Fetch a single session by its *session_id* and *user_id*.

        Args:
            session_id: The ``_id`` of the session (string).
            user_id: Identifier of the owning user.

        Returns:
            dict or None: The session document, or ``None`` if not found
                          or on error.
        """
        try:
            return self.sessions.find_one(
                {"_id": ObjectId(session_id), "user_id": user_id},
                projection={"_id": 1, "user_id": 1, "title": 1, "created_at": 1, "updated_at": 1, "is_active": 1},
            )
        except pymongo.errors.PyMongoError as exc:
            logger.error("get_session failed for session %s: %s", session_id, exc)
            return None
        except Exception:
            return None

    def delete_session(self, session_id, user_id):
        """Delete a session and all its messages.

        Args:
            session_id: The ``_id`` of the session (string).
            user_id: Identifier of the owning user.

        Returns:
            bool: ``True`` on success, ``False`` on failure.
        """
        try:
            self.sessions.delete_one({"_id": ObjectId(session_id), "user_id": user_id})
            self.messages.delete_many({"session_id": session_id})
            return True
        except pymongo.errors.PyMongoError as exc:
            logger.error("delete_session failed for session %s: %s", session_id, exc)
            return False
        except Exception:
            return False

    def update_session_title(self, session_id, title):
        """Update the display title of a session.

        Args:
            session_id: The ``_id`` of the session (string).
            title: New title string.
        """
        try:
            self.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"title": title}},
            )
        except pymongo.errors.PyMongoError as exc:
            logger.error("update_session_title failed for session %s: %s", session_id, exc)
        except Exception:
            pass

    def update_session(self, session_id, update_fields):
        """Update arbitrary fields on a session document.

        Automatically sets ``updated_at`` to the current UTC time.

        Args:
            session_id: The ``_id`` of the session (string).
            update_fields: Dictionary of fields to set.

        Returns:
            bool: ``True`` if a document was matched and updated,
                  ``False`` otherwise.
        """
        try:
            update_fields["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
            result = self.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": update_fields},
            )
            return result.matched_count > 0
        except pymongo.errors.PyMongoError as exc:
            logger.error("update_session failed for session %s: %s", session_id, exc)
            return False

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def add_message(self, session_id, role, content):
        """Append a message to a session and touch its *updated_at* field.

        Args:
            session_id: The ``_id`` of the parent session (string).
            role: Message role (e.g. ``"user"``, ``"assistant"``).
            content: Message body text.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            self.messages.insert_one({
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": now,
            })
        except pymongo.errors.PyMongoError as exc:
            logger.error("add_message insert failed for session %s: %s", session_id, exc)
            return

        try:
            self.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc)}},
            )
        except pymongo.errors.PyMongoError as exc:
            logger.warning("add_message session touch failed for session %s: %s", session_id, exc)
        except Exception:
            pass

    def get_messages(self, session_id):
        """Return all messages for a session, ordered by timestamp.

        Args:
            session_id: The ``_id`` of the parent session (string).

        Returns:
            list[dict]: Each dict contains ``role``, ``content``, and
                        ``timestamp`` (ISO string).
        """
        try:
            docs = self.messages.find(
                {"session_id": session_id},
                projection={"_id": 0, "role": 1, "content": 1, "timestamp": 1},
            ).sort("timestamp", 1)
            results = []
            for m in docs:
                ts = m.get("timestamp")
                results.append({
                    "role": m["role"],
                    "content": m["content"],
                    "timestamp": ts.isoformat() if isinstance(ts, datetime.datetime) else str(ts),
                })
            return results
        except pymongo.errors.PyMongoError as exc:
            logger.error("get_messages failed for session %s: %s", session_id, exc)
            return []

    def update_message(self, message_id, new_content):
        """Update the content of an existing message.

        Args:
            message_id: The ``_id`` of the message (string).
            new_content: New message body text.

        Returns:
            bool: ``True`` if the message was found and updated,
                  ``False`` otherwise.
        """
        try:
            result = self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {
                    "content": new_content,
                    "edited_at": datetime.datetime.now(datetime.timezone.utc),
                }},
            )
            return result.matched_count > 0
        except pymongo.errors.PyMongoError as exc:
            logger.error("update_message failed for message %s: %s", message_id, exc)
            return False

    def delete_message(self, message_id):
        """Delete a single message by its ``_id``.

        Args:
            message_id: The ``_id`` of the message (string).

        Returns:
            bool: ``True`` if the message was deleted, ``False`` otherwise.
        """
        try:
            result = self.messages.delete_one({"_id": ObjectId(message_id)})
            return result.deleted_count > 0
        except pymongo.errors.PyMongoError as exc:
            logger.error("delete_message failed for message %s: %s", message_id, exc)
            return False

    def delete_session_messages(self, session_id):
        """Delete all messages belonging to a session.

        Args:
            session_id: The ``_id`` of the parent session (string).

        Returns:
            int: Number of messages deleted, or ``-1`` on error.
        """
        try:
            result = self.messages.delete_many({"session_id": session_id})
            return result.deleted_count
        except pymongo.errors.PyMongoError as exc:
            logger.error("delete_session_messages failed for session %s: %s", session_id, exc)
            return -1

    # ------------------------------------------------------------------
    # User settings
    # ------------------------------------------------------------------

    def get_user_settings(self, user_id):
        """Retrieve settings for *user_id*, returning defaults if absent.

        Args:
            user_id: Identifier of the user.

        Returns:
            dict: Settings document with at least ``user_id``,
                  ``preferred_language``, and ``personal_api_key``.
        """
        defaults = {"user_id": user_id, "preferred_language": "Python", "personal_api_key": ""}
        try:
            s = self.user_settings.find_one(
                {"user_id": user_id},
                projection={"_id": 0, "user_id": 1, "preferred_language": 1, "personal_api_key": 1},
            )
            if not s:
                return defaults
            return s
        except pymongo.errors.PyMongoError as exc:
            logger.error("get_user_settings failed for user %s: %s", user_id, exc)
            return defaults
        except Exception:
            return defaults

    def save_user_settings(self, user_id, preferred_language, personal_api_key):
        """Upsert user settings (create or update).

        Args:
            user_id: Identifier of the user.
            preferred_language: Preferred programming language string.
            personal_api_key: User's personal API key string.
        """
        try:
            self.user_settings.update_one(
                {"user_id": user_id},
                {"$set": {
                    "preferred_language": preferred_language,
                    "personal_api_key": personal_api_key,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }},
                upsert=True,
            )
        except pymongo.errors.PyMongoError as exc:
            logger.error("save_user_settings failed for user %s: %s", user_id, exc)

    # Keep backward-compatible alias
    update_user_settings = save_user_settings


mongo_store = MongoStore()  # Safe — no network call at import time