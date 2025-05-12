import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

class Database:
    def __init__(self, db_path: str = "chat.db"):
        """Khởi tạo kết nối database"""
        self.db_path = db_path
        self.conn = None
        self.setup_database()
        
    def setup_database(self):
        """Thiết lập database và tạo các bảng"""
        try:
            # Tạo thư mục database nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Kết nối database
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Trả về rows dạng dict
            
            # Đọc và thực thi schema
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            with open(schema_path, 'r') as f:
                self.conn.executescript(f.read())
            self.conn.commit()
            
        except Exception as e:
            logging.error(f"Database setup error: {e}")
            raise
            
    def close(self):
        """Đóng kết nối database"""
        if self.conn:
            self.conn.close()
            
    # User operations
    def create_user(self, username: str, peer_ip: str, peer_port: int) -> Optional[int]:
        """Tạo user mới"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, peer_ip, peer_port)
                VALUES (?, ?, ?)
            """, (username, peer_ip, peer_port))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        except Exception as e:
            logging.error(f"Create user error: {e}")
            return None
            
    def get_user(self, username: str) -> Optional[Dict]:
        """Lấy thông tin user theo username"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"Get user error: {e}")
            return None
            
    def update_user_status(self, username: str, peer_ip: str, peer_port: int):
        """Cập nhật thông tin kết nối của user"""
        try:
            self.conn.execute("""
                UPDATE users 
                SET peer_ip = ?, peer_port = ?, last_seen = CURRENT_TIMESTAMP
                WHERE username = ?
            """, (peer_ip, peer_port, username))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Update user status error: {e}")
            return False
            
    # Channel operations
    def create_channel(self, name: str, created_by: int, is_default: bool = False) -> Optional[int]:
        """Tạo channel mới"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO channels (name, created_by, is_default)
                VALUES (?, ?, ?)
            """, (name, created_by, is_default))
            
            channel_id = cursor.lastrowid
            
            # Thêm người tạo vào channel_members
            cursor.execute("""
                INSERT INTO channel_members (channel_id, user_id)
                VALUES (?, ?)
            """, (channel_id, created_by))
            
            self.conn.commit()
            return channel_id
        except Exception as e:
            logging.error(f"Create channel error: {e}")
            return None
            
    def get_channel(self, channel_id: int) -> Optional[Dict]:
        """Lấy thông tin channel theo ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT c.*, u.username as creator_name
                FROM channels c
                JOIN users u ON c.created_by = u.id
                WHERE c.id = ?
            """, (channel_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"Get channel error: {e}")
            return None
            
    def get_user_channels(self, user_id: int) -> List[Dict]:
        """Lấy danh sách channel của user"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT c.*, u.username as creator_name
                FROM channels c
                JOIN channel_members cm ON c.id = cm.channel_id
                JOIN users u ON c.created_by = u.id
                WHERE cm.user_id = ?
                ORDER BY c.created_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Get user channels error: {e}")
            return []
            
    def set_default_channel(self, user_id: int, channel_id: int) -> bool:
        """Đặt channel mặc định cho user"""
        try:
            self.conn.execute("""
                UPDATE users
                SET default_channel_id = ?
                WHERE id = ?
            """, (channel_id, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Set default channel error: {e}")
            return False
            
    # Message operations
    def add_message(self, channel_id: int, user_id: int, content: str, 
                   message_type: str = 'text') -> Optional[int]:
        """Thêm tin nhắn mới"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO messages (channel_id, user_id, content, message_type)
                VALUES (?, ?, ?, ?)
            """, (channel_id, user_id, content, message_type))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logging.error(f"Add message error: {e}")
            return None
            
    def get_channel_messages(self, channel_id: int, limit: int = 100) -> List[Dict]:
        """Lấy tin nhắn của channel"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT m.*, u.username
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.channel_id = ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, (channel_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Get channel messages error: {e}")
            return []
            
    def get_recent_messages(self, channel_id: int, since_timestamp: float) -> List[Dict]:
        """Lấy tin nhắn mới từ thời điểm chỉ định"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT m.*, u.username
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.channel_id = ? AND m.timestamp > datetime(?, 'unixepoch')
                ORDER BY m.timestamp ASC
            """, (channel_id, since_timestamp))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Get recent messages error: {e}")
            return []
            
    # Channel member operations
    def add_channel_member(self, channel_id: int, user_id: int) -> bool:
        """Thêm user vào channel"""
        try:
            self.conn.execute("""
                INSERT INTO channel_members (channel_id, user_id)
                VALUES (?, ?)
            """, (channel_id, user_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return True  # User đã là thành viên
        except Exception as e:
            logging.error(f"Add channel member error: {e}")
            return False
            
    def remove_channel_member(self, channel_id: int, user_id: int) -> bool:
        """Xóa user khỏi channel"""
        try:
            self.conn.execute("""
                DELETE FROM channel_members
                WHERE channel_id = ? AND user_id = ?
            """, (channel_id, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Remove channel member error: {e}")
            return False
            
    def get_channel_members(self, channel_id: int) -> List[Dict]:
        """Lấy danh sách thành viên của channel"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT u.*, cm.joined_at
                FROM users u
                JOIN channel_members cm ON u.id = cm.user_id
                WHERE cm.channel_id = ?
                ORDER BY cm.joined_at ASC
            """, (channel_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Get channel members error: {e}")
            return [] 