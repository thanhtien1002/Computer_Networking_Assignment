import customtkinter as ctk
import tkinter as tk
from threading import Thread
import logging
import requests
import json
import time
import os
from datetime import datetime
import emoji
import pygame
from tkinter import filedialog
from PIL import Image, ImageTk
import io
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from .config import *
import socket
import tkinter.messagebox as messagebox

class ChatWindow:
    def __init__(self, username, server_ip, server_port, channel_id, start_stream_callback, send_message_callback, is_visitor=False):
        self.username = username
        self.server_ip = server_ip
        self.server_port = server_port
        self.current_channel = channel_id
        self.start_stream_callback = start_stream_callback
        self.send_message_callback = send_message_callback
        self.is_visitor = is_visitor
        
        self.running = True
        self.channels = {}
        self.channel_messages = {}
        self.unread_channels = set()
        self.typing_users = set()
        self.default_channel = None
        
        self.streaming = {
            'active': False,
            'thread': None
        }

        self.connection_retry = {
            'max_retries': 3,
            'retry_delay': 1.0,
            'current_retries': 0
        }

        self.session = requests.Session()
        self.session.mount('http://', requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=10,
            pool_maxsize=10
        ))
        
        self.is_dark_mode = True
        self.typing_users = set()
        self.channels = {}  # {channel_id: channel_name}
        self.current_channel = channel_id
        self.channel_messages = {}  # {channel_id: [messages]}
        self.unread_channels = set()  # Channels with unread messages
        
        # Khởi tạo pygame cho sound effects
        self._init_sounds()
        
        # Cấu hình logging
        self._setup_logging()
        
        # Thiết lập theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Tạo cửa sổ chính
        self.root = ctk.CTk()
        self.root.title(WINDOW_TITLE + (" (Visitor Mode)" if is_visitor else ""))
        self.root.geometry(CHAT_WINDOW_SIZE)
        
        # Lấy kênh mặc định từ server
        self._get_default_channel()
        
        # Tạo layout
        self.create_layout()
        
        # Bắt đầu các thread cập nhật
        self._start_update_threads()
        
    def _init_sounds(self):
        pygame.mixer.init()
        self.sounds_enabled = True
        try:
            # Tạo thư mục sounds nếu chưa tồn tại
            if not os.path.exists('sounds'):
                os.makedirs('sounds')
                
            # Kiểm tra và tạo file âm thanh mặc định nếu không tồn tại
            sound_files = {
                'message.wav': b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00',
                'notification.wav': b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
            }
            
            for filename, default_data in sound_files.items():
                filepath = os.path.join('sounds', filename)
                if not os.path.exists(filepath):
                    with open(filepath, 'wb') as f:
                        f.write(default_data)
                        
            self.message_sound = pygame.mixer.Sound('sounds/message.wav')
            self.notification_sound = pygame.mixer.Sound('sounds/notification.wav')
        except Exception as e:
            logging.warning(f"Sound initialization failed: {e}")
            self.sounds_enabled = False
        
    def _setup_logging(self):
        # Tạo thư mục logs nếu chưa tồn tại
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Cấu hình logging cho chat với UTF-8 encoding
        self.chat_logger = logging.getLogger('chat')
        self.chat_logger.setLevel(logging.INFO)
        log_file = f'logs/chat_{datetime.now().strftime("%Y%m%d")}.log'
        chat_handler = logging.FileHandler(log_file, encoding=DEFAULT_ENCODING)
        chat_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.chat_logger.addHandler(chat_handler)
        
    def _start_update_threads(self):
        # Bắt đầu thread cập nhật tin nhắn và kênh
        self.update_thread = Thread(target=self.update_messages_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        self.channel_update_thread = Thread(target=self.update_channels_loop)
        self.channel_update_thread.daemon = True
        self.channel_update_thread.start()
        
        # Thêm thread gửi heartbeat
        self.heartbeat_thread = Thread(target=self.heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        # Thêm thread cập nhật danh sách user
        self.user_update_thread = Thread(target=self.update_user_list_loop)
        self.user_update_thread.daemon = True
        self.user_update_thread.start()
        
    def create_layout(self):
        # Main container
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left sidebar for channels
        self._create_sidebar(main_container)
        
        # Main chat area
        self._create_chat_area(main_container)
        
        # Right sidebar for user list
        self._create_user_list(main_container)
        
    def _create_sidebar(self, parent):
        self.sidebar = ctk.CTkFrame(parent, width=250, corner_radius=0)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), pady=0)
        
        # Server name và logo
        server_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        server_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # Logo (emoji)
        logo_label = ctk.CTkLabel(
            server_frame,
            text="��",
            font=(FONT_FAMILY, 32)
        )
        logo_label.pack(side=tk.LEFT, padx=5)
        
        # Server name
        server_label = ctk.CTkLabel(
            server_frame,
            text=WINDOW_TITLE,
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold")
        )
        server_label.pack(side=tk.LEFT, padx=5)
        
        # Separator
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color=THEME_COLORS["dark"]["text_secondary"])
        separator.pack(fill=tk.X, padx=10, pady=10)
        
        # Channel list header với search
        channel_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        channel_header.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Search frame
        search_frame = ctk.CTkFrame(channel_header, fg_color="transparent")
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Search icon
        search_icon = ctk.CTkLabel(
            search_frame,
            text="🔍",
            font=(FONT_FAMILY, FONT_SIZE_SMALL)
        )
        search_icon.pack(side=tk.LEFT, padx=(5, 0))
        
        # Search entry
        self.channel_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search channels...",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            height=30,
            corner_radius=15
        )
        self.channel_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.channel_search.bind('<KeyRelease>', self._filter_channels)
        
        # Channel header với nút tạo mới
        channel_title_frame = ctk.CTkFrame(channel_header, fg_color="transparent")
        channel_title_frame.pack(fill=tk.X)
        
        channel_label = ctk.CTkLabel(
            channel_title_frame,
            text="CHANNELS",
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            text_color=THEME_COLORS["dark"]["text_secondary"]
        )
        channel_label.pack(side=tk.LEFT, padx=5)
        
        if not self.is_visitor:
            add_channel_btn = ctk.CTkButton(
                channel_title_frame,
                text="+",
                width=30,
                height=30,
                corner_radius=15,
                command=self.show_add_channel_dialog,
                fg_color=THEME_COLORS["dark"]["accent"],
                hover_color=THEME_COLORS["dark"]["accent"]
            )
            add_channel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Channel list
        self._create_channel_list()
        
    def _filter_channels(self, event=None):
        search_text = self.channel_search.get().lower()
        self.update_channel_list(search_text)

    def _create_channel_list(self):
        # Channel list container với scrollbar
        self.channel_list = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color=THEME_COLORS["dark"]["accent"],
            scrollbar_button_hover_color=THEME_COLORS["dark"]["accent"]
        )
        self.channel_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def _create_chat_area(self, parent):
        chat_area = ctk.CTkFrame(parent, fg_color="transparent")
        chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=0)
        
        # Header với thông tin user và controls
        self._create_chat_header(chat_area)
        
        # Message area
        self._create_message_area(chat_area)
        
        # Input area
        self._create_input_area(chat_area)
        
    def _create_chat_header(self, parent):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Channel info
        self.channel_label = ctk.CTkLabel(
            header_frame,
            text=f"# {self.current_channel}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold")
        )
        self.channel_label.pack(side=tk.LEFT, padx=10)
        
        # User info
        user_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        user_frame.pack(side=tk.RIGHT, padx=10)
        
        # Online status indicator
        self.status_indicator = ctk.CTkLabel(
            user_frame,
            text="●",
            text_color="green",
            font=(FONT_FAMILY, FONT_SIZE)
        )
        self.status_indicator.pack(side=tk.LEFT, padx=5)
        
        user_label = ctk.CTkLabel(
            user_frame,
            text=f"👤 {self.username}" + (" (Visitor)" if self.is_visitor else ""),
            font=(FONT_FAMILY, FONT_SIZE)
        )
        user_label.pack(side=tk.LEFT, padx=5)
        
        # Theme toggle
        theme_button = ctk.CTkButton(
            user_frame,
            text="🌙" if self.is_dark_mode else "☀️",
            width=30,
            height=30,
            corner_radius=15,
            command=self.toggle_theme
        )
        theme_button.pack(side=tk.LEFT, padx=5)
        
    def _create_message_area(self, parent):
        self.message_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.message_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Message list với scrollbar
        self.message_list = ctk.CTkTextbox(
            self.message_frame,
            font=(FONT_FAMILY, FONT_SIZE),
            wrap=tk.WORD,
            height=400,
            corner_radius=10
        )
        self.message_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Typing indicator
        self.typing_label = ctk.CTkLabel(
            self.message_frame,
            text="",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=THEME_COLORS["dark"]["text_secondary"]
        )
        self.typing_label.pack(side=tk.BOTTOM, padx=5, pady=2)
        
    def _create_input_area(self, parent):
        control_frame = ctk.CTkFrame(parent, fg_color="transparent")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        if not self.is_visitor:
            # Emoji button
            emoji_button = ctk.CTkButton(
                control_frame,
                text="😊",
                width=40,
                height=40,
                corner_radius=20,
                command=self.show_emoji_picker
            )
            emoji_button.pack(side=tk.LEFT, padx=5)
            
            # File button
            file_button = ctk.CTkButton(
                control_frame,
                text="📎",
                width=40,
                height=40,
                corner_radius=20,
                command=self.attach_file
            )
            file_button.pack(side=tk.LEFT, padx=5)
            
            # Message entry
            self.message_entry = ctk.CTkEntry(
                control_frame,
                placeholder_text="Nhập tin nhắn...",
                font=(FONT_FAMILY, FONT_SIZE),
                height=40,
                corner_radius=20
            )
            self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))
            self.message_entry.bind('<Return>', lambda e: self.send_message())
            self.message_entry.bind('<Key>', self.on_typing)
            
            # Send button
            send_button = ctk.CTkButton(
                control_frame,
                text="Gửi",
                font=(FONT_FAMILY, FONT_SIZE, "bold"),
                height=40,
                corner_radius=20,
                command=self.send_message
            )
            send_button.pack(side=tk.LEFT, padx=5)
            
            # Stream button
            self.stream_button = ctk.CTkButton(
                control_frame,
                text="Bắt đầu Stream",
                font=(FONT_FAMILY, FONT_SIZE, "bold"),
                height=40,
                corner_radius=20,
                command=self.toggle_stream
            )
            self.stream_button.pack(side=tk.LEFT, padx=5)
        else:
            # Visitor message
            visitor_label = ctk.CTkLabel(
                control_frame,
                text="Bạn đang ở chế độ xem. Chỉ có thể xem tin nhắn.",
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
                text_color=THEME_COLORS["dark"]["text_secondary"]
            )
            visitor_label.pack(side=tk.LEFT, padx=10)
            
    def _create_user_list(self, parent):
        """Tạo khung hiển thị danh sách người dùng"""
        self.user_list_frame = ctk.CTkFrame(parent, width=200, corner_radius=0)
        self.user_list_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0), pady=0)
        
        # Header
        user_header = ctk.CTkFrame(self.user_list_frame, fg_color="transparent")
        user_header.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        user_label = ctk.CTkLabel(
            user_header,
            text="ONLINE USERS",
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            text_color=THEME_COLORS["dark"]["text_secondary"]
        )
        user_label.pack(side=tk.LEFT, padx=5)
        
        # User list container
        self.user_list = ctk.CTkScrollableFrame(self.user_list_frame, fg_color="transparent")
        self.user_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Dictionary để lưu trữ các widget user
        self.user_widgets = {}
        self.stream_windows = {}  # Lưu trữ các cửa sổ stream đang mở

    def show_add_channel_dialog(self):
        dialog = ctk.CTkInputDialog(
            text="Enter channel name:",
            title="Create New Channel",
            font=("Roboto", 14)
        )
        channel_name = dialog.get_input()
        if channel_name:
            try:
                response = requests.post(
                    f'http://{self.server_ip}:5000/channels',
                    json={'name': channel_name}
                )
                if response.status_code == 200:
                    self.update_channels()
            except Exception as e:
                logging.error(f"Error creating channel: {e}")
                
    def update_channels(self):
        self.connection_retry['current_retries'] = 0
        while True:
            try:
                response = self.session.get(
                    f'http://{self.server_ip}:5000/channels',
                    timeout=5.0
                )
                response.raise_for_status()
                channels = response.json()
                
                # Cập nhật channels
                self.channels = {str(channel['id']): channel for channel in channels}
                self.update_channel_list()
                return True
            except requests.exceptions.RequestException as e:
                if not self._handle_connection_error(e, "updating channels"):
                    return False
            except Exception as e:
                logging.error(f"Error updating channels: {e}")
                return False
            
    def update_channel_list(self, search_text="", force_redraw=False):
        """
        Cập nhật danh sách kênh
        :param search_text: Từ khóa tìm kiếm
        :param force_redraw: Có vẽ lại toàn bộ danh sách không
        """
        # Nếu không có thay đổi và không bắt buộc vẽ lại, chỉ cập nhật trạng thái
        if not force_redraw:
            for widget in self.channel_list.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    channel_frame = widget
                    channel_id = None
                    
                    # Tìm channel_id từ button command
                    for child in channel_frame.winfo_children():
                        if isinstance(child, ctk.CTkButton):
                            try:
                                command = child.cget('command')
                                if command and callable(command):
                                    channel_id = command.__closure__[0].cell_contents
                                    break
                            except:
                                continue
                    
                    if channel_id:
                        # Cập nhật trạng thái unread
                        has_unread = channel_id in self.unread_channels and channel_id != self.current_channel
                        has_badge = False
                        
                        # Kiểm tra xem đã có badge chưa
                        for child in channel_frame.winfo_children():
                            if isinstance(child, ctk.CTkLabel) and child.cget('text') == "●":
                                has_badge = True
                                if not has_unread:
                                    child.destroy()
                                break
                        
                        # Thêm badge nếu cần
                        if has_unread and not has_badge:
                            badge = ctk.CTkLabel(
                                channel_frame,
                                text="●",
                                text_color="red",
                                font=(FONT_FAMILY, FONT_SIZE_SMALL)
                            )
                            badge.pack(side=tk.RIGHT, padx=5)
            return
            
        # Vẽ lại toàn bộ danh sách nếu cần
        for widget in self.channel_list.winfo_children():
            widget.destroy()
            
        # Thêm các channel buttons mới
        for channel_id, channel_name in self.channels.items():
            if search_text and search_text not in channel_name.lower():
                continue
                
            # Channel frame để chứa button và badge
            channel_frame = ctk.CTkFrame(self.channel_list, fg_color="transparent")
            channel_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Channel button với style mới
            btn = ctk.CTkButton(
                channel_frame,
                text=f"# {channel_name}" + (" (Home)" if channel_id == self.default_channel else ""),
                font=(FONT_FAMILY, FONT_SIZE),
                height=40,
                corner_radius=20,
                command=lambda cid=channel_id: self.switch_channel(cid),
                fg_color="transparent" if channel_id != self.current_channel else THEME_COLORS["dark"]["accent"],
                hover_color=THEME_COLORS["dark"]["accent"] if channel_id != self.current_channel else None,
                text_color=THEME_COLORS["dark"]["text"] if channel_id != self.current_channel else "white"
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Context menu cho channel
            if not self.is_visitor:
                menu_btn = ctk.CTkButton(
                    channel_frame,
                    text="⋮",
                    width=30,
                    height=30,
                    corner_radius=15,
                    command=lambda cid=channel_id: self.show_channel_menu(cid),
                    fg_color="transparent",
                    hover_color=THEME_COLORS["dark"]["accent"]
                )
                menu_btn.pack(side=tk.RIGHT, padx=2)
            
            # Unread badge
            if channel_id in self.unread_channels and channel_id != self.current_channel:
                badge = ctk.CTkLabel(
                    channel_frame,
                    text="●",
                    text_color="red",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL)
                )
                badge.pack(side=tk.RIGHT, padx=5)
            
    def switch_channel(self, channel_id):
        if channel_id == self.current_channel:
            return
            
        self.current_channel = channel_id
        self.channel_label.configure(text=f"# {self.channels.get(channel_id, channel_id)}")
        
        # Xóa trạng thái unread
        if channel_id in self.unread_channels:
            self.unread_channels.remove(channel_id)
            
        # Cập nhật UI
        self.update_channel_list()
        self.message_list.delete('1.0', tk.END)
        
        # Hiển thị tin nhắn của kênh mới
        if channel_id in self.channel_messages:
            for msg in self.channel_messages[channel_id]:
                timestamp = datetime.fromtimestamp(msg['timestamp']).strftime('%H:%M')
                message_text = f"[{timestamp}] {msg['username']}: {msg['message']}\n"
                self.message_list.insert(tk.END, message_text)
                
        # Cuộn xuống cuối
        self.message_list.see(tk.END)
        
        # Cập nhật danh sách user
        self.update_user_list()
        
    def update_channels_loop(self):
        last_channels = {}  # Cache danh sách kênh cũ
        while self.running:
            try:
                response = requests.get(f'http://{self.server_ip}:5000/channels')
                if response.status_code == 200:
                    channels = {c['id']: c['name'] for c in response.json()}
                    
                    # Chỉ cập nhật UI nếu danh sách kênh thay đổi
                    if channels != last_channels:
                        self.channels = channels
                        last_channels = channels.copy()
                        self.update_channel_list(force_redraw=True)
                        
                time.sleep(5)  # Cập nhật mỗi 5 giây
            except Exception as e:
                logging.error(f"Error in update_channels_loop: {e}")
                time.sleep(5)
                
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        ctk.set_appearance_mode("dark" if self.is_dark_mode else "light")
        self.root.update()
        
    def show_emoji_picker(self):
        # Tạo popup window cho emoji picker
        emoji_window = ctk.CTkToplevel(self.root)
        emoji_window.title("Emoji Picker")
        emoji_window.geometry("300x400")
        
        # Frame cho emoji grid
        emoji_frame = ctk.CTkFrame(emoji_window)
        emoji_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Thêm các emoji phổ biến
        common_emojis = ["😊", "😂", "❤️", "👍", "👋", "🎉", "🔥", "💯"]
        for i, emoji_text in enumerate(common_emojis):
            btn = ctk.CTkButton(
                emoji_frame,
                text=emoji_text,
                width=40,
                height=40,
                command=lambda e=emoji_text: self.insert_emoji(e, emoji_window)
            )
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)
            
    def insert_emoji(self, emoji_text, window):
        current_text = self.message_entry.get()
        self.message_entry.delete(0, tk.END)
        self.message_entry.insert(0, current_text + emoji_text)
        window.destroy()
        
    def attach_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            # Xử lý file đính kèm
            file_name = os.path.basename(file_path)
            self.message_entry.delete(0, tk.END)
            self.message_entry.insert(0, f"[File: {file_name}]")
            
    def on_typing(self, event):
        # Gửi typing status
        if event.keysym not in ['Return', 'BackSpace', 'Delete']:
            self.typing_users.add(self.username)
            self.update_typing_indicator()
            
    def update_typing_indicator(self):
        if self.typing_users:
            users = ", ".join(self.typing_users)
            self.typing_label.configure(text=f"{users} is typing...")
        else:
            self.typing_label.configure(text="")
            
    def send_message(self):
        message = self.message_entry.get()
        if message:
            # Gửi tin nhắn
            self.send_message_callback(
                self.server_ip,
                self.server_port,
                self.username,
                message,
                self.current_channel
            )
            # Lưu vào log
            self.chat_logger.info(f"{self.username}: {message}")
            # Xóa nội dung entry
            self.message_entry.delete(0, tk.END)
            # Phát sound nếu enabled
            if self.sounds_enabled:
                try:
                    self.message_sound.play()
                except:
                    pass
            
    def toggle_stream(self):
        if not self.streaming['active']:
            self.start_stream()
        else:
            self.stop_stream()
            
    def start_stream(self):
        self.streaming['active'] = True
        self.stream_button.configure(text="Stop Stream")
        self.streaming['thread'] = Thread(
            target=lambda: self.start_stream_callback(
                self.server_ip,
                self.server_port,
                self.streaming
            )
        )
        self.streaming['thread'].daemon = True
        self.streaming['thread'].start()
        
    def stop_stream(self):
        if self.streaming['active']:
            self.streaming['active'] = False
            self.stream_button.configure(text="Start Stream")
            if self.streaming['thread'] and self.streaming['thread'].is_alive():
                self.streaming['thread'].join(timeout=1.0)
                
    def get_messages(self, channel_id=None):
        if channel_id is None:
            channel_id = self.current_channel
            
        self.connection_retry['current_retries'] = 0
        while True:
            try:
                response = self.session.get(
                    f'http://{self.server_ip}:5000/channels/{channel_id}/messages',
                    timeout=5.0
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if not self._handle_connection_error(e, "getting messages"):
                    return []
            except Exception as e:
                logging.error(f"Error getting messages: {e}")
                return []
            
    def update_messages_loop(self):
        while self.running:
            try:
                for channel_id in self.channels.keys():
                    messages = self.get_messages(channel_id)
                    
                    if not messages and self.connection_retry['current_retries'] >= self.connection_retry['max_retries']:
                        continue
                        
                    # Cập nhật tin nhắn
                    if channel_id not in self.channel_messages:
                        self.channel_messages[channel_id] = []
                    
                    if len(messages) > len(self.channel_messages[channel_id]):
                        new_messages = messages[len(self.channel_messages[channel_id]):]
                        self.channel_messages[channel_id] = messages
                        
                        if channel_id == self.current_channel:
                            for msg in new_messages:
                                self._display_message(msg)
                        else:
                            if channel_id not in self.unread_channels:
                                self.unread_channels.add(channel_id)
                                self.update_channel_list()
                
                time.sleep(1.0)
            except Exception as e:
                logging.error(f"Error in update_messages_loop: {e}")
                time.sleep(1.0)
                
    def on_closing(self):
        self.running = False
        if self.streaming['active']:
            self.stop_stream()
        self.root.quit()
        
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop() 

    def _get_default_channel(self):
        try:
            client_socket = socket.socket()
            client_socket.connect((self.server_ip, self.server_port))
            client_socket.send(json.dumps({
                'type': 'GET_DEFAULT_CHANNEL',
                'username': self.username
            }).encode('utf-8'))
            response = json.loads(client_socket.recv(1024).decode('utf-8'))
            client_socket.close()
            
            if response['status'] == 'OK':
                self.default_channel = response['channel_id']
                self.current_channel = self.default_channel
        except Exception as e:
            logging.error(f"Error getting default channel: {e}")

    def go_to_home_channel(self):
        if self.default_channel:
            self.switch_channel(self.default_channel)

    def set_default_channel(self, channel_id):
        try:
            client_socket = socket.socket()
            client_socket.connect((self.server_ip, self.server_port))
            client_socket.send(json.dumps({
                'type': 'SET_DEFAULT_CHANNEL',
                'username': self.username,
                'channel_id': channel_id
            }).encode('utf-8'))
            response = json.loads(client_socket.recv(1024).decode('utf-8'))
            client_socket.close()
            
            if response['status'] == 'OK':
                self.default_channel = channel_id
                messagebox.showinfo("Success", "Default channel updated!")
            else:
                messagebox.showerror("Error", "Could not update default channel")
        except Exception as e:
            logging.error(f"Error setting default channel: {e}")
            messagebox.showerror("Error", "Could not update default channel")

    def show_channel_menu(self, channel_id):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="Set as Home Channel" if channel_id != self.default_channel else "Already Home Channel",
            command=lambda: self.set_default_channel(channel_id),
            state=tk.NORMAL if channel_id != self.default_channel else tk.DISABLED
        )
        menu.add_separator()
        menu.add_command(label="Delete Channel", command=lambda: self.delete_channel(channel_id))
        
        # Hiển thị menu tại vị trí chuột
        menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def delete_channel(self, channel_id):
        if channel_id == self.default_channel:
            messagebox.showerror("Error", "Cannot delete home channel")
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this channel?"):
            try:
                response = requests.delete(f'http://{self.server_ip}:5000/channels/{channel_id}')
                if response.status_code == 200:
                    if channel_id == self.current_channel:
                        self.go_to_home_channel()
                    if channel_id in self.channels:
                        del self.channels[channel_id]
                    if channel_id in self.channel_messages:
                        del self.channel_messages[channel_id]
                    if channel_id in self.unread_channels:
                        self.unread_channels.remove(channel_id)
                    self.update_channel_list()
            except Exception as e:
                logging.error(f"Error deleting channel: {e}")
                messagebox.showerror("Error", "Could not delete channel")

    def _handle_connection_error(self, error, operation):
        """Xử lý lỗi kết nối"""
        if self.connection_retry['current_retries'] < self.connection_retry['max_retries']:
            self.connection_retry['current_retries'] += 1
            logging.warning(f"Connection error during {operation}. Retrying {self.connection_retry['current_retries']}/{self.connection_retry['max_retries']}")
            time.sleep(self.connection_retry['retry_delay'])
            return True
        else:
            logging.error(f"Connection failed after {self.connection_retry['max_retries']} retries: {error}")
            messagebox.showerror("Connection Error", f"Failed to connect to server after {self.connection_retry['max_retries']} attempts")
            return False

    def _display_message(self, msg):
        """Hiển thị tin nhắn lên UI"""
        try:
            timestamp = datetime.fromtimestamp(msg['timestamp']).strftime('%H:%M')
            message_text = f"[{timestamp}] {msg['username']}: {msg['message']}\n"
            
            self.message_list.insert(tk.END, message_text)
            self.message_list.see(tk.END)
            self.chat_logger.info(message_text.strip())
            
            if msg['username'] != self.username and self.sounds_enabled:
                try:
                    self.notification_sound.play()
                except:
                    pass
        except Exception as e:
            logging.error(f"Error displaying message: {e}")

    def heartbeat_loop(self):
        """Gửi heartbeat định kỳ để duy trì trạng thái online"""
        while self.running:
            try:
                client_socket = socket.socket()
                client_socket.connect((self.server_ip, self.server_port))
                client_socket.send(json.dumps({
                    'type': 'HEARTBEAT',
                    'username': self.username
                }).encode('utf-8'))
                response = json.loads(client_socket.recv(1024).decode('utf-8'))
                client_socket.close()
                
                if response['status'] == 'OK':
                    self.status_indicator.configure(text_color="green")
                else:
                    self.status_indicator.configure(text_color="red")
                    
                time.sleep(10)  # Gửi heartbeat mỗi 10 giây
            except Exception as e:
                logging.error(f"Error in heartbeat: {e}")
                self.status_indicator.configure(text_color="red")
                time.sleep(10) 

    def update_user_list(self):
        """Cập nhật danh sách người dùng"""
        try:
            # Lấy danh sách peers từ server
            client_socket = socket.socket()
            client_socket.connect((self.server_ip, self.server_port))
            client_socket.send(json.dumps({'type': 'GET_LIST'}).encode('utf-8'))
            peers = json.loads(client_socket.recv(1024).decode('utf-8'))['peers']
            client_socket.close()
            
            # Xóa các widget cũ
            for widget in self.user_list.winfo_children():
                widget.destroy()
            self.user_widgets.clear()
            
            # Thêm các user mới
            for peer in peers:
                user_frame = ctk.CTkFrame(self.user_list, fg_color="transparent")
                user_frame.pack(fill=tk.X, padx=5, pady=2)
                
                # Status indicator
                status_color = "green" if peer.get('is_online', False) else "red"
                status_indicator = ctk.CTkLabel(
                    user_frame,
                    text="●",
                    text_color=status_color,
                    font=(FONT_FAMILY, FONT_SIZE_SMALL)
                )
                status_indicator.pack(side=tk.LEFT, padx=5)
                
                # Username
                username = peer['username']
                user_label = ctk.CTkLabel(
                    user_frame,
                    text=username,
                    font=(FONT_FAMILY, FONT_SIZE_SMALL)
                )
                user_label.pack(side=tk.LEFT, padx=5)
                
                # Streaming indicator và View Live button
                if peer.get('is_streaming', False):
                    stream_indicator = ctk.CTkLabel(
                        user_frame,
                        text="🎥",
                        font=(FONT_FAMILY, FONT_SIZE_SMALL)
                    )
                    stream_indicator.pack(side=tk.RIGHT, padx=5)
                    
                    # Thêm nút View Live nếu người dùng đang stream
                    view_live_btn = ctk.CTkButton(
                        user_frame,
                        text="View Live",
                        width=80,
                        height=25,
                        corner_radius=12,
                        font=(FONT_FAMILY, FONT_SIZE_SMALL),
                        command=lambda p=peer: self.view_live_stream(p)
                    )
                    view_live_btn.pack(side=tk.RIGHT, padx=5)
                
                # Lưu widget để cập nhật sau
                self.user_widgets[username] = {
                    'frame': user_frame,
                    'status': status_indicator,
                    'label': user_label
                }
                
        except Exception as e:
            logging.error(f"Error updating user list: {e}")

    def view_live_stream(self, peer):
        """Xem livestream của người dùng"""
        try:
            # Kiểm tra nếu đã có cửa sổ stream cho người dùng này
            if peer['username'] in self.stream_windows:
                return
                
            # Tạo cửa sổ stream mới
            stream_window = ctk.CTkToplevel(self.root)
            stream_window.title(f"Live Stream - {peer['username']}")
            stream_window.geometry("640x480")
            
            # Frame cho video
            video_frame = ctk.CTkFrame(stream_window)
            video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Label hiển thị video
            video_label = ctk.CTkLabel(video_frame, text="Connecting to stream...")
            video_label.pack(fill=tk.BOTH, expand=True)
            
            # Lưu thông tin cửa sổ
            self.stream_windows[peer['username']] = {
                'window': stream_window,
                'frame': video_frame,
                'label': video_label
            }
            
            # Xử lý khi đóng cửa sổ
            def on_closing():
                if peer['username'] in self.stream_windows:
                    del self.stream_windows[peer['username']]
                stream_window.destroy()
                
            stream_window.protocol("WM_DELETE_WINDOW", on_closing)
            
            # Bắt đầu nhận stream
            self.start_stream_callback(
                self.server_ip,
                self.server_port,
                {
                    'active': True,
                    'peer': peer,
                    'window': stream_window,
                    'frame': video_frame,
                    'label': video_label
                }
            )
            
        except Exception as e:
            logging.error(f"Error viewing live stream: {e}")
            messagebox.showerror("Error", f"Could not connect to stream: {str(e)}")

    def update_user_list_loop(self):
        """Cập nhật danh sách user định kỳ"""
        while self.running:
            try:
                self.update_user_list()
                time.sleep(5)  # Cập nhật mỗi 5 giây
            except Exception as e:
                logging.error(f"Error in update_user_list_loop: {e}")
                time.sleep(5) 