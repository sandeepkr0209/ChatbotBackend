import pymongo
from pymongo import MongoClient
from datetime import datetime
import os

# Set up MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client.get_database("chatbot_db")
users_collection = db["users"]
conversation_collection = db["conversations"]
journal_collection = db["journals"]

# Store user details (name, email, preferences)
def store_user_details(user_id, name, email="", preferences=None):
    """Store or update user profile."""
    user_data = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "preferences": preferences or {},
        "updated_at": datetime.utcnow()
    }
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": user_data},
        upsert=True
    )
    print("✅ User details stored/updated.")

# Store conversation (user message and bot message)
def store_conversation(user_id, user_message, bot_message):
    """Store messages between user and bot."""
    conversation_data = {
        "user_id": user_id,
        "messages": [
            {"sender": "user", "message": user_message, "timestamp": datetime.utcnow()},
            {"sender": "bot", "message": bot_message, "timestamp": datetime.utcnow()},
        ],
        "bot_message": bot_message,
        "timestamp": datetime.utcnow()
    }
    conversation_collection.insert_one(conversation_data)
    print("✅ Conversation stored.")

# Get user conversation history (limit to last 'n' messages)
def get_user_history(user_id, limit=5):
    """Get user's recent conversation history."""
    history = conversation_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
    return [entry["messages"] for entry in history]

# Retrieve user name from the database
def get_user_name(user_id):
    """Retrieve user name."""
    user = users_collection.find_one({"user_id": user_id})
    return user["name"] if user else "friend"

# Retrieve user preferences (like notifications, relaxation tools)
def get_user_preferences(user_id):
    """Retrieve stored preferences."""
    user = users_collection.find_one({"user_id": user_id})
    return user.get("preferences", {}) if user else {}

# Store a journal entry made by the user
def store_journal_entry(user_id, entry):
    """Save a journaling response."""
    journal_data = {
        "user_id": user_id,
        "entry": entry,
        "timestamp": datetime.utcnow()
    }
    journal_collection.insert_one(journal_data)
    print("✅ Journal entry stored.")

# Retrieve the user's recent journal entries (limit to last 'n' entries)
def get_journal_entries(user_id, limit=5):
    """Get recent journal entries."""
    entries = journal_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
    return [{"entry": e["entry"], "timestamp": e["timestamp"]} for e in entries]

# Example for initializing and testing the functions
if __name__ == "__main__":
    # Example usage
    user_id = "12345"
    name = "John Doe"
    email = "johndoe@example.com"
    preferences = {"notifications": True, "relaxation_tools": ["breathing", "meditation"]}

    # Store user details
    store_user_details(user_id, name, email, preferences)

    # Store a conversation
    store_conversation(user_id, "I'm feeling stressed", "Let's do a breathing exercise.")

    # Store a journal entry
    store_journal_entry(user_id, "I feel more relaxed after the exercise.")

    # Retrieve conversations and journal entries
    print(get_user_history(user_id))
    print(get_journal_entries(user_id))
