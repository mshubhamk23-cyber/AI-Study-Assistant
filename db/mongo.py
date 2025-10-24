import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

def init_db():
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI not found in environment variables")

    # Connect
    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=3000
    )

    try:
        client.admin.command("ping")
        print("✅ MongoDB connected successfully")
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        raise RuntimeError(f"❌ MongoDB connection failed: {e}")

    # Always return a database object explicitly
    return client["student_ai_assistant"]
