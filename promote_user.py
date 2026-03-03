"""
Synapse AI — Superuser Promotion Utility
Usage: python promote_user.py <username>
This script promotes a MongoDB user to Superuser status.
Once promoted, log in to the website to gain Admin Panel access.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

def promote(username):
    uri = os.getenv('MONGO_URI')
    if not uri:
        print("Error: MONGO_URI not found in .env")
        return

    client = MongoClient(uri)
    try:
        # Detect database name from URI or default
        db_name = uri.split('/')[-1].split('?')[0] or "synapse_mongo"
        db = client[db_name]
        users = db.users

        user = users.find_one({"username": username})
        if not user:
            print(f"Error: User '{username}' not found in MongoDB.")
            return

        print(f"User found: {username} ({user.get('email', 'no email')})")
        
        result = users.update_one(
            {"username": username},
            {"$set": {
                "is_staff": True,
                "is_superuser": True
            }}
        )

        if result.modified_count > 0:
            print(f"SUCCESS: User '{username}' is now a Superuser.")
            print("Action: Now log in to your website. The Admin status will sync automatically!")
        else:
            if user.get('is_superuser'):
                print(f"Notice: User '{username}' is ALREADY a Superuser.")
            else:
                print("Error: Could not update user.")

    except Exception as e:
        print(f"Connection Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promote_user.py <username>")
    else:
        promote(sys.argv[1])
