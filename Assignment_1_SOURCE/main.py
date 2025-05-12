import argparse
import logging
from threading import Thread
from ui.chat_window import ChatWindow
from streaming.video_stream import VideoStream
import requests
import json
import time
import socket
import sys
import os
from node import thread_server, thread_client, send_message, get_messages
from config_manager import config

# Ẩn terminal window
if sys.platform == 'win32':
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Cấu hình logging
logging.basicConfig(
    filename='peer_log.txt', 
    level=getattr(logging, config.get_logging_config().get('level', 'INFO')),
    format='%(asctime)s - %(message)s'
)

def check_port(peer_ip, peer_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((peer_ip, peer_port))
        s.close()
        return True
    except OSError as e:
        print(f"Port {peer_port} is already in use: {e}")
        return False
    finally:
        s.close()

def main():
    parser = argparse.ArgumentParser(description="P2P Segment Chat Node")
    parser.add_argument('--peer-port', type=int, default=config.get_peer_config().get('default_peer_port'), 
                       help='Port for peer server')
    parser.add_argument('--server-port', type=int, default=config.get_tracker_config().get('socket_port'), 
                       help='Port for tracker server')
    parser.add_argument('--flask-port', type=int, default=config.get_tracker_config().get('flask_port'), 
                       help='Port for Flask server')
    parser.add_argument('--server-ip', type=str, required=True, help='IP address of tracker server')
    parser.add_argument('--peer-ip', type=str, required=True, help='IP address of this peer')
    parser.add_argument('--visitor', action='store_true', help='Run as visitor (read-only mode)')
    args = parser.parse_args()
    
    # Cấu hình mạng
    peer_ip = args.peer_ip
    peer_port = args.peer_port
    server_ip = args.server_ip
    server_port = args.server_port
    flask_port = args.flask_port
    channel_id = config.get_peer_config().get('default_channel_id')
    
    # Kiểm tra port
    if not check_port(peer_ip, peer_port):
        print(f"Port {peer_port} is already in use. Please choose a different port.")
        return
        
    # Nhập tên người dùng
    username = input("Enter your username: ").strip()
    if not username:
        username = config.get_peer_config().get('default_username')
        
    # Kết nối với tracker
    success, message = thread_client(1, server_ip, server_port, peer_ip, peer_port, username, 
                                   config.get_peer_config().get('default_session_id'))
    if not success:
        print(f"Failed to connect to tracker: {message}")
        return
        
    # Khởi động video stream handler
    video_stream = VideoStream(username)
    
    # Bắt đầu thread nhận stream
    receive_thread = Thread(
        target=lambda: video_stream.start_receiving(peer_ip, peer_port, server_ip, server_port),
        daemon=True
    )
    receive_thread.start()
    
    # Khởi tạo và chạy giao diện chat
    chat_window = ChatWindow(
        username=username,
        server_ip=server_ip,
        server_port=server_port,
        channel_id=channel_id,
        start_stream_callback=lambda server_ip, server_port, streaming_state: video_stream.start_sending(server_ip, server_port, streaming_state),
        send_message_callback=send_message,
        is_visitor=args.visitor
    )
    
    # Bắt đầu thread server
    server_thread = Thread(target=thread_server, args=(peer_ip, peer_port))
    server_thread.daemon = True
    server_thread.start()
    
    try:
        chat_window.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Cleanup khi thoát
        video_stream.cleanup()
        if receive_thread.is_alive():
            receive_thread.join(timeout=1.0)
        if server_thread.is_alive():
            server_thread.join(timeout=1.0)

if __name__ == "__main__":
    main() 