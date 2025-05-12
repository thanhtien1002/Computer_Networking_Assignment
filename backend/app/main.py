# backend/app/main.py
from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, get_db
from .models import User, Message, Channel
from typing import List
import sqlite3
from datetime import datetime
from passlib.context import CryptContext

app = FastAPI()

# Cập nhật CORS để cho phép cả localhost:3000 và localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
init_db()

@app.post("/api/login")
async def login(user: User):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
        result = cursor.fetchone()
        if result and pwd_context.verify(user.password, result[1]):
            cursor.execute("UPDATE users SET status = 'online' WHERE username = ?", 
                           (user.username,))
            conn.commit()
            return {"status": "success", "user": {"username": user.username, "mode": "authenticated"}}
        raise HTTPException(status_code=401, detail="Tên người dùng hoặc mật khẩu không đúng")

@app.post("/api/register")
async def register(user: User):
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="Tên người dùng và mật khẩu là bắt buộc")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự")
    if len(user.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Tên người dùng phải có ít nhất 3 ký tự")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Tên người dùng đã tồn tại")
        
        hashed_password = pwd_context.hash(user.password)
        cursor.execute("INSERT INTO users (username, password, status) VALUES (?, ?, ?)", 
                       (user.username, hashed_password, "online"))
        conn.commit()
        return {"status": "success", "user": {"username": user.username, "mode": "authenticated"}}

@app.get("/api/channels", response_model=List[Channel])
async def get_channels():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels")
        channels = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        if not channels:
            cursor.execute("INSERT INTO channels (id, name) VALUES (?, ?)", 
                           ("1", "Channel 1"))
            conn.commit()
            channels = [{"id": "1", "name": "Channel 1"}]
        return channels

@app.post("/api/channels/{channel_id}/messages")
async def send_message(channel_id: str, message: Message):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND status = 'online'", 
                       (message.user,))
        if not cursor.fetchone():
            raise HTTPException(status_code=403, detail="Yêu cầu đăng nhập để gửi tin nhắn")
        cursor.execute("INSERT INTO messages (channel_id, user, text, timestamp) VALUES (?, ?, ?, ?)",
                       (channel_id, message.user, message.text, message.timestamp))
        conn.commit()
        with open("connection.log", "a") as f:
            f.write(f"Message sent: {message.user} -> Channel {channel_id}\n")
        return {"status": "success"}

@app.get("/api/channels/{channel_id}/messages", response_model=List[Message])
async def get_messages(channel_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user, text, timestamp FROM messages WHERE channel_id = ?", 
                       (channel_id,))
        messages = [{"user": row[0], "text": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
        return messages

connected_peers = {}

@app.websocket("/ws/{peer_id}")
async def websocket_endpoint(websocket: WebSocket, peer_id: str):
    await websocket.accept()
    connected_peers[peer_id] = websocket
    try:
        while True:
            data = await websocket.receive_json()
            for pid, peer_ws in connected_peers.items():
                if pid != peer_id:
                    await peer_ws.send_json(data)
    except Exception as e:
        print(f"Error with WebSocket: {e}")
    finally:
        del connected_peers[peer_id]
        await websocket.close() 