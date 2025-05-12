import socket
import json
import time
import logging
from threading import Thread
from flask import Flask, jsonify, request
import signal
import sys
from werkzeug.serving import make_server
from config_manager import config
from datetime import datetime
import atexit

# Cấu hình logging
logger = logging.getLogger('tracker')
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler('tracker_log.txt')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(console_handler)

app = Flask(__name__)
peers = []  # [{peer_ip, peer_port, username, session_id, is_streaming, is_receiving, is_online, last_seen}]
messages = {}  # {channel_id: [{username, message, timestamp}]}
channels = {}  # {channel_id: {name, created_by, created_at}}
user_channels = {}  # {username: default_channel_id}
running = True
serversocket = None
flask_server = None

# Biến toàn cục để theo dõi kết nối
active_connections = set()

# Thời gian timeout cho trạng thái online (30 giây)
ONLINE_TIMEOUT = 30

def check_online_status():
    """Kiểm tra và cập nhật trạng thái online của các peer"""
    current_time = time.time()
    for peer in peers:
        if peer.get('last_seen') and current_time - peer['last_seen'] > ONLINE_TIMEOUT:
            peer['is_online'] = False
            logger.info(f"User {peer['username']} is now offline")

def log_connection(addr, action):
    """Log connection activity"""
    logger.info(f"{addr[0]}:{addr[1]} - {action}")

def log_message(addr, msg_data):
    """Log message activity"""
    logger.info(f"{addr[0]}:{addr[1]} - {msg_data}")

def check_port(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        s.close()
        return True
    except OSError as e:
        print(f"Port {port} is already in use: {e}")
        return False
    finally:
        s.close()

def signal_handler(sig, frame):
    """Xử lý khi server bị tắt"""
    global running, serversocket, flask_server
    logger.info("Server shutting down...")
    running = False
    
    # Đóng socket server
    if serversocket is not None:
        try:
            serversocket.close()
            logger.info("Socket server closed")
        except:
            pass
            
    # Đóng Flask server
    if flask_server is not None:
        try:
            flask_server.shutdown()
            logger.info("Flask server stopped")
        except:
            pass
            
    # Cleanup các kết nối
    cleanup_connections()
    logger.info("Cleanup completed")
    sys.exit(0)

@app.before_request
def before_request():
    """Xử lý trước mỗi request"""
    cleanup_connections()
    check_online_status()

@app.after_request
def after_request(response):
    """Xử lý sau mỗi request"""
    try:
        # Thêm headers để tránh cache
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error in after_request: {e}")
        return response

@app.errorhandler(Exception)
def handle_error(error):
    """Xử lý lỗi chung"""
    logger.error(f"Unhandled error: {error}")
    return jsonify({'error': str(error)}), 500

def cleanup_connections():
    """Dọn dẹp các kết nối không còn hoạt động"""
    try:
        for conn in list(active_connections):
            try:
                conn.send(b'')
            except:
                active_connections.remove(conn)
                logger.info(f"Removed dead connection")
    except Exception as e:
        logger.error(f"Error in cleanup_connections: {e}")

def terminal_input_handler():
    global running, serversocket, flask_server
    while running:
        try:
            command = input().strip().lower()
            if command == "quit":
                print("Stopping tracker...")
                running = False
                if serversocket is not None:
                    try:
                        serversocket.close()
                    except:
                        pass
                if flask_server is not None:
                    flask_server.shutdown()
                sys.exit(0)
        except EOFError:
            pass
        except KeyboardInterrupt:
            signal_handler(None, None)

def new_connection(addr, conn):
    global running
    while running:
        try:
            data = conn.recv(1024).decode('utf-8')
            if not data or not running:
                break
            request = json.loads(data)
            if request['type'] == 'SUBMIT_INFO':
                username = request['username']
                if any(peer['username'] == username for peer in peers):
                    conn.send(json.dumps({'status': 'ERROR', 'message': 'Username already taken'}).encode('utf-8'))
                else:
                    # Tạo kênh mặc định cho người dùng mới nếu chưa có
                    if username not in user_channels:
                        channel_id = str(int(time.time() * 1000))
                        channels[channel_id] = {
                            'id': channel_id,
                            'name': f'home_{username}',
                            'created_by': username,
                            'created_at': time.time(),
                            'is_default': True
                        }
                        user_channels[username] = channel_id
                        messages[channel_id] = []  # Khởi tạo mảng tin nhắn trống cho kênh mới
                    
                    peers.append({
                        'peer_ip': request['peer_ip'],
                        'peer_port': request['peer_port'],
                        'username': username,
                        'session_id': request['session_id'],
                        'is_streaming': False,
                        'is_receiving': False,
                        'is_online': True,
                        'last_seen': time.time(),
                        'default_channel': user_channels[username]
                    })
                    log_connection(addr, 'SUBMIT_INFO')
                    conn.send(json.dumps({
                        'status': 'OK',
                        'default_channel': user_channels[username]
                    }).encode('utf-8'))
            elif request['type'] == 'HEARTBEAT':
                username = request['username']
                for peer in peers:
                    if peer['username'] == username:
                        peer['last_seen'] = time.time()
                        peer['is_online'] = True
                        break
                conn.send(json.dumps({'status': 'OK'}).encode('utf-8'))
            elif request['type'] == 'GET_DEFAULT_CHANNEL':
                username = request['username']
                if username in user_channels:
                    conn.send(json.dumps({
                        'status': 'OK',
                        'channel_id': user_channels[username]
                    }).encode('utf-8'))
                else:
                    conn.send(json.dumps({
                        'status': 'ERROR',
                        'message': 'No default channel found'
                    }).encode('utf-8'))
            elif request['type'] == 'SET_DEFAULT_CHANNEL':
                username = request['username']
                channel_id = request['channel_id']
                if channel_id in channels:
                    user_channels[username] = channel_id
                    conn.send(json.dumps({'status': 'OK'}).encode('utf-8'))
                else:
                    conn.send(json.dumps({
                        'status': 'ERROR',
                        'message': 'Channel not found'
                    }).encode('utf-8'))
            elif request['type'] == 'GET_LIST':
                # Cập nhật trạng thái online trước khi gửi danh sách
                check_online_status()
                conn.send(json.dumps({'peers': peers}).encode('utf-8'))
            elif request['type'] == 'GET_CHANNELS':
                conn.send(json.dumps({'channels': list(channels.values())}).encode('utf-8'))
            elif request['type'] == 'CREATE_CHANNEL':
                channel_id = str(int(time.time() * 1000))
                channels[channel_id] = {
                    'id': channel_id,
                    'name': request['name'],
                    'created_by': request.get('username', 'anonymous'),
                    'created_at': time.time(),
                    'is_default': False
                }
                conn.send(json.dumps({'status': 'OK', 'channel': channels[channel_id]}).encode('utf-8'))
            elif request['type'] == 'SUBMIT_MESSAGE':
                channel_id = request['channel_id']
                if channel_id not in messages:
                    messages[channel_id] = []
                messages[channel_id].append({
                    'username': request['username'],
                    'message': request['message'],
                    'timestamp': request['timestamp']
                })
                log_message(addr, request)
                conn.send(json.dumps({'status': 'OK'}).encode('utf-8'))
            elif request['type'] == 'GET_MESSAGES':
                channel_id = request['channel_id']
                response = {'messages': messages.get(channel_id, [])}
                conn.send(json.dumps(response).encode('utf-8'))
            elif request['type'] == 'UPDATE_STREAM_STATUS':
                username = request['username']
                for peer in peers:
                    if peer['username'] == username:
                        peer['is_streaming'] = request['is_streaming']
                        peer['is_receiving'] = request['is_receiving']
                        peer['last_seen'] = time.time()
                        peer['is_online'] = True
                        break
                conn.send(json.dumps({'status': 'OK'}).encode('utf-8'))
        except:
            break
    conn.close()

def server_program(host, port):
    global running, serversocket
    
    # Khởi tạo socket server
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind((host, port))
    serversocket.listen(5)
    
    logger.info(f'Socket server started on {host}:{port}')
    
    # Thread cho input từ terminal
    terminal_thread = Thread(target=terminal_input_handler)
    terminal_thread.daemon = True
    terminal_thread.start()
    
    while running:
        try:
            serversocket.settimeout(1.0)
            conn, addr = serversocket.accept()
            active_connections.add(conn)
            Thread(target=new_connection, args=(addr, conn)).start()
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                logger.error(f"Error accepting connection: {e}")
            break

# REST API
@app.route('/channels', methods=['GET'])
def get_channels():
    return jsonify(list(channels.values()))

@app.route('/channels', methods=['POST'])
def create_channel():
    data = request.json
    channel_id = str(int(time.time() * 1000))  # Unique ID based on timestamp
    channels[channel_id] = {
        'id': channel_id,
        'name': data['name'],
        'created_by': data.get('username', 'anonymous'),
        'created_at': time.time()
    }
    return jsonify(channels[channel_id])

@app.route('/channels/<channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    if channel_id in channels:
        del channels[channel_id]
        if channel_id in messages:
            del messages[channel_id]
        return jsonify({'status': 'OK'})
    return jsonify({'status': 'ERROR', 'message': 'Channel not found'}), 404

@app.route('/channels/<channel_id>/messages', methods=['GET'])
def get_messages(channel_id):
    return jsonify(messages.get(channel_id, []))

@app.route('/channels/<channel_id>/messages', methods=['POST'])
def post_message(channel_id):
    data = request.json
    if channel_id not in messages:
        messages[channel_id] = []
    messages[channel_id].append({
        'username': data['username'],
        'message': data['message'],
        'timestamp': time.time()
    })
    log_message(('API', 0), data)
    return jsonify({'status': 'OK'})

class FlaskServerThread(Thread):
    def __init__(self, app, host, port):
        Thread.__init__(self)
        self.srv = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        logger.info('Starting Flask server...')
        self.srv.serve_forever()

    def shutdown(self):
        self.srv.shutdown()

if __name__ == '__main__':
    # Đăng ký signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Khởi động Flask server
    flask_server = FlaskServerThread(app, '127.0.0.1', 5000)
    flask_server.daemon = True
    flask_server.start()
    
    # Khởi động socket server
    try:
        server_program('127.0.0.1', config.get_tracker_config().get('socket_port', 5001))
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)