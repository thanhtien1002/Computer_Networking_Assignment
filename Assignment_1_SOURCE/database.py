from pymongo import MongoClient
from datetime import datetime
import hashlib

client = MongoClient("localhost",27017)

db = client.database

collection = db.contact_info

chat_history = db.chat_history

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def add_info(peer_ip, port_ip, username, password):
    """Add new user to database"""
    hashed_password = hash_password(password)
    return collection.insert_one({
        "peer_ip": peer_ip,
        "port_ip": port_ip,
        "user_name": username,
        "password": hashed_password,
        "created_at": datetime.now()
    })

def check_username_exist(username):
    """Check if username already exists"""
    user = collection.find_one({"user_name": username})
    return user is not None

def check_password(username):
    """Get hashed password for username"""
    user = collection.find_one({"user_name": username})
    return user.get("password") if user else None

def verify_password(username, password):
    """Verify password for username"""
    hashed_password = hash_password(password)
    stored_password = check_password(username)
    return stored_password == hashed_password if stored_password else False

def get_history_chat():
    """Get chat history"""
    history = chat_history.find().sort("timestamp", -1).limit(50)

    # Thu thập các document vào một danh sách Python
    messages = [
        {
            "username": msg["username"],
            "message": msg["message"],
            "timestamp": msg["timestamp"].isoformat()  # Chuyển timestamp thành chuỗi
        }
        for msg in history
    ]

    return messages

def add_into_chat_his(username, message, timestamp):
    """Add message to chat history"""
    return chat_history.insert_one({
        "username": username,
        "message": message,
        "timestamp": timestamp
    })