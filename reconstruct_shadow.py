import os
import django
import datetime
from bson.objectid import ObjectId

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synapse_project.settings')
django.setup()

from django.contrib.auth.models import User as DjangoUser
from chat.models import ChatSession, ChatMessage
from chat.mongo_store import mongo_store

def reconstruct():
    print("--- Synapse AI: Shadow Reconstruction Starting ---")
    
    # 1. Sync Users
    print("Syncing Users from MongoDB...")
    mongo_users = list(mongo_store.users.find({}))
    for u_doc in mongo_users:
        username = u_doc['username']
        DjangoUser.objects.update_or_create(
            username=username,
            defaults={
                "email": u_doc.get('email', ''),
                "password": u_doc.get('password', ''),
                "is_staff": u_doc.get('is_staff', False),
                "is_superuser": u_doc.get('is_superuser', False),
                "is_active": True
            }
        )
    print(f"Synced {len(mongo_users)} users.")

    # 2. Sync Chat Sessions
    print("Syncing Chat Sessions from MongoDB...")
    mongo_sessions = list(mongo_store.sessions.find({}))
    synced_sessions = 0
    for s_doc in mongo_sessions:
        try:
            u_name = s_doc['user_id']
            u_sql = DjangoUser.objects.filter(username=u_name).first()
            if not u_sql:
                continue
                
            s_id_str = str(s_doc['_id'])
            # Derive a consistent integer ID from the MongoDB ObjectId string
            s_id_int = int(s_id_str[:8], 16) % 2147483647
            
            ChatSession.objects.update_or_create(
                id=s_id_int,
                defaults={
                    "user": u_sql,
                    "title": s_doc.get('title', 'New Chat'),
                    "is_active": s_doc.get('is_active', True),
                    "created_at": s_doc.get('created_at', datetime.datetime.utcnow()),
                    "updated_at": s_doc.get('updated_at', datetime.datetime.utcnow()),
                }
            )
            synced_sessions += 1
        except Exception:
            import traceback
            traceback.print_exc()
            print(f"Error syncing session {s_doc.get('_id')}")

    print(f"Synced {synced_sessions} sessions.")

    # 3. Sync Recent Messages (Top 100 per session to keep SQLite light)
    print("Syncing Recent Messages from MongoDB...")
    total_messages = 0
    for s_doc in mongo_sessions:
        s_id_str = str(s_doc['_id'])
        s_id_int = int(s_id_str[:8], 16) % 2147483647
        s_sql = ChatSession.objects.filter(id=s_id_int).first()
        
        if s_sql:
            # Get messages for this session
            m_docs = list(mongo_store.messages.find({"session_id": s_id_str}).sort("timestamp", -1).limit(50))
            for m_doc in reversed(m_docs):
                ChatMessage.objects.get_or_create(
                    session=s_sql,
                    role=m_doc['role'],
                    content=m_doc['content'],
                    defaults={"timestamp": m_doc.get('timestamp', datetime.datetime.utcnow())}
                )
                total_messages += 1
                
    print(f"Synced {total_messages} recent messages.")
    print("✅ Shadow Reconstruction Complete.")

if __name__ == "__main__":
    reconstruct()
