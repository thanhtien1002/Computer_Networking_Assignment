import socket
import json
import time
import logging
import tkinter as tk
from threading import Thread
import cv2
import numpy as np
import pickle
import requests
import argparse
import signal
import sys
import tkinter.messagebox as messagebox
from threading import Thread
from database import add_into_chat_his


# Cấu hình logging
logging.basicConfig(filename='peer_log.txt', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

# Biến để kiểm soát việc dừng chương trình
running = True
root = None  # Biến toàn cục để lưu Tkinter root

def log_connection(addr, action):
    logging.info(f"{addr[0]}:{addr[1]} - {action}")
    with open('peer_log.txt', 'r') as f:
        if sum(1 for _ in f) > 10000:
            open('peer_log.txt', 'w').close()

def check_port(peer_ip, peer_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind((peer_ip, peer_port))
        s.close()
        return True
    except OSError as e:
        print(f"Port {peer_port} is already in use: {e}")
        return False
    finally:
        s.close()

def signal_handler(sig, frame):
    global running
    print("\nStopping program...")
    running = False
    cv2.destroyAllWindows()
    if root is not None:
        root.destroy()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def terminal_input_handler():
    global running
    while running:
        try:
            command = input().strip().lower()
            if command == "quit":
                print("Stopping program...")
                running = False
                cv2.destroyAllWindows()
                if root is not None:
                    root.destroy()
                sys.exit(0)
        except EOFError:
            pass  # Xử lý khi terminal bị đóng
        except KeyboardInterrupt:
            signal_handler(None, None)

def update_streaming_status(server_ip, server_port, username, is_streaming=False, is_receiving=False):
    try:
        client_socket = socket.socket()
        client_socket.connect((server_ip, server_port))
        client_socket.send(json.dumps({
            'type': 'UPDATE_STREAM_STATUS',
            'username': username,
            'is_streaming': is_streaming,
            'is_receiving': is_receiving
        }).encode('utf-8'))
        response = json.loads(client_socket.recv(1024).decode('utf-8'))
        client_socket.close()
        return response['status'] == 'OK'
    except Exception as e:
        logging.error(f"Error updating streaming status: {e}")
        print(f"Error updating streaming status: {e}")
        return False

def thread_server(peer_ip, peer_port):
    global running
    
    if not check_port(peer_ip, peer_port):
        print(f"Cannot bind to port {peer_port}. Exiting...")
        sys.exit(1)
    try:
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind((peer_ip, peer_port))
        
        # Tạo cửa sổ cho receiver với kích thước cố định
        window_name = None
        last_frame_time = time.time()
        
        while running:
            serversocket.settimeout(1.0)
            try:
                data, addr = serversocket.recvfrom(65507)
                if not running:
                    break
                    
                try:
                    # Thử parse dữ liệu frame
                    received_data = pickle.loads(data)
                    if isinstance(received_data, dict) and 'frame' in received_data:
                        last_frame_time = time.time()  # Cập nhật thời gian nhận frame cuối
                        frame = cv2.imdecode(np.frombuffer(received_data['frame'], np.uint8), cv2.IMREAD_COLOR)
                        sender_username = received_data.get('sender_username', 'Unknown')
                        if frame is not None:
                            # Tạo cửa sổ nếu chưa có
                            if window_name is None:
                                window_name = f"[RECEIVING] Stream from {sender_username}"
                                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                            
                            # Hiển thị frame nhận được
                            cv2.imshow(window_name, frame)
                            key = cv2.waitKey(1) & 0xFF
                            if key == ord('q'):
                                if window_name:
                                    cv2.destroyWindow(window_name)
                                    window_name = None
                                break
                        else:
                            print("Error: Invalid frame data")
                    
                    # Kiểm tra nếu không nhận được frame mới trong 3 giây
                    if window_name and time.time() - last_frame_time > 3:
                        print("Stream ended - No frames received for 3 seconds")
                        cv2.destroyWindow(window_name)
                        window_name = None
                        
                except pickle.UnpicklingError:
                    # Nếu không phải frame data, xử lý như message thông thường
                    try:
                        request = json.loads(data.decode('utf-8'))
                        if request['type'] == 'PEER_STREAM':
                            log_connection(addr, 'PEER_STREAM')
                            last_frame_time = time.time()  # Reset thời gian khi bắt đầu stream mới
                    except json.JSONDecodeError:
                        print("Error: Invalid message format")
                        
            except socket.timeout:
                # Kiểm tra timeout cho stream đang chạy
                if window_name and time.time() - last_frame_time > 3:
                    print("Stream ended - No frames received for 3 seconds")
                    cv2.destroyWindow(window_name)
                    window_name = None
                continue
                
    except Exception as e:
        logging.error(f"Error in thread_server: {e}")
        print(f"Error in thread_server: {e}")
    finally:
        if window_name:
            cv2.destroyWindow(window_name)
        serversocket.close()
        cv2.destroyAllWindows()

def thread_client(id, server_ip, server_port, peer_ip, peer_port, username, session_id, is_visitor=False):
    global running
    try:
        if not running:
            return False, "Program stopped"
        client_socket = socket.socket()
        client_socket.connect((server_ip, server_port))
        client_socket.send(json.dumps({
            'type': 'SUBMIT_INFO',
            'peer_ip': peer_ip,
            'peer_port': peer_port,
            'username': username,
            'session_id': session_id,
            'is_visitor': is_visitor
        }).encode('utf-8'))
        response = json.loads(client_socket.recv(1024).decode('utf-8'))
        client_socket.close()
        if response['status'] == 'ERROR':
            return False, response['message']
        return True, "OK"
    except Exception as e:
        logging.error(f"Error in thread_client: {e}")
        print(f"Error in thread_client: {e}")
        return False, str(e)

def send_message(server_ip, server_port, username, message, channel_id):
    try:
        client_socket = socket.socket()
        client_socket.connect((server_ip, server_port))
        client_socket.send(json.dumps({
            'type': 'SUBMIT_MESSAGE',
            'username': username,
            'message': message,
            'timestamp': time.time(),
            'channel_id': channel_id
        }).encode('utf-8'))
        add_into_chat_his(
            username=username,
            message=message,
            timestamp=time.time()
        )
        client_socket.close()
    except Exception as e:
        logging.error(f"Error in send_message: {e}")
        print(f"Error in send_message: {e}")

def get_messages(server_ip, channel_id):
    try:
        response = requests.get(f'http://{server_ip}:5000/channels/{channel_id}/messages')
        return response.json()
    except:
        return []

def bot_response(message):
    if message.lower() == 'hi':
        return 'Hello'
    return None

def get_username():
    def submit_username():
        nonlocal username
        username = entry.get().strip()
        if not username:
            username = "user1"
        elif not username.isalnum():
            messagebox.showerror("Error", "Username must contain only letters and numbers")
            return
        root.destroy()

    root = tk.Tk()
    root.title("Enter Username")
    tk.Label(root, text="Please enter your username:").pack(pady=10)
    entry = tk.Entry(root)
    entry.pack(pady=5)
    tk.Button(root, text="Submit", command=submit_username).pack(pady=5)
    username = "user1"
    root.mainloop()
    return username

def create_ui(username, server_ip, server_port, channel_id, is_visitor=False):
    global running, root
    root = tk.Tk()
    root.title("Segment Chat" + (" (Visitor Mode)" if is_visitor else ""))
    
    # Tạo frame cho các controls
    control_frame = tk.Frame(root)
    control_frame.pack(fill=tk.X, padx=5, pady=5)
    
    # Label hiển thị tên người dùng
    tk.Label(root, text=f"User: {username}" + (" (Visitor)" if is_visitor else "")).pack()
    
    # Text area cho tin nhắn
    message_list = tk.Text(root, height=10)
    message_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Frame cho input và nút
    input_frame = tk.Frame(root)
    input_frame.pack(fill=tk.X, padx=5, pady=5)
    
    if not is_visitor:
        # Entry cho tin nhắn
        entry = tk.Entry(input_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Nút gửi tin nhắn
        tk.Button(input_frame, text="Send", 
                command=lambda: send_message(server_ip, server_port, username, entry.get(), channel_id)
        ).pack(side=tk.LEFT, padx=5)
        
        # Nút điều khiển stream
        stream_btn = tk.Button(input_frame, text="Start Stream", command=lambda: start_stream(server_ip, server_port))
        stream_btn.pack(side=tk.LEFT, padx=5)
    else:
        # Thông báo cho visitor
        visitor_label = tk.Label(
            input_frame,
            text="You are in visitor mode. You can only view messages and streams.",
            fg="gray"
        )
        visitor_label.pack(side=tk.LEFT, padx=5)
    
    def update_messages():
        if not running:
            root.destroy()
            return
        messages = get_messages(server_ip, channel_id)
        message_list.delete(1.0, tk.END)
        for msg in messages:
            message_list.insert(tk.END, f"{msg['username']}: {msg['message']}\n")
            bot_msg = bot_response(msg['message'])
            if bot_msg:
                send_message(server_ip, server_port, 'Bot', bot_msg, channel_id)
        root.after(1000, update_messages)
    
    def on_closing():
        global running
        running = False
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    update_messages()
    root.mainloop()

def start_stream(server_ip, server_port, streaming_state=None):
    try:
        client_socket = socket.socket()
        client_socket.connect((server_ip, server_port))
        client_socket.send(json.dumps({'type': 'GET_LIST'}).encode('utf-8'))
        peers = json.loads(client_socket.recv(1024).decode('utf-8'))['peers']
        client_socket.close()
        
        if not peers:
            print("No peers available for streaming")
            logging.warning("No peers available for streaming")
            if streaming_state:
                streaming_state['active'] = False
            return
            
        # Chọn một người làm sender
        sender = next((peer for peer in peers if not peer['is_streaming'] and peer['username'] == username), None)
        if not sender:
            print("You are already streaming or cannot stream at this moment")
            if streaming_state:
                streaming_state['active'] = False
            return
            
        # Những người còn lại sẽ là receivers
        receivers = [peer for peer in peers if peer['username'] != username]
        
        if not receivers:
            print("No receivers available")
            if streaming_state:
                streaming_state['active'] = False
            return

        # Tạo UDP socket cho việc gửi stream
        stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Bắt đầu stream video
        cap = cv2.VideoCapture('sample_video.mp4')
        if not cap.isOpened():
            print("Error: No video source available")
            if streaming_state:
                streaming_state['active'] = False
            return

        # Cập nhật trạng thái streaming cho sender
        update_streaming_status(server_ip, server_port, username, is_streaming=True)
        
        print(f"Started streaming to {len(receivers)} peers")
        
        # Tạo cửa sổ cho sender với kích thước cố định
        window_name = f"[SENDING] Your Stream ({username})"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        # Stream đến tất cả receivers
        while cap.isOpened() and running:
            # Kiểm tra nếu người dùng đã dừng stream
            if streaming_state and not streaming_state['active']:
                break
                
            ret, frame = cap.read()
            if not ret:
                # Nếu video kết thúc, quay lại từ đầu
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            # Nén frame và gửi đến tất cả receivers
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            frame_data = pickle.dumps({
                'frame': buffer,
                'sender_username': username
            })
            
            for receiver in receivers:
                try:
                    stream_socket.sendto(frame_data, (receiver['peer_ip'], receiver['peer_port']))
                except Exception as e:
                    print(f"Error sending to {receiver['username']}: {e}")
                    
            # Hiển thị frame cho sender
            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                if streaming_state:
                    streaming_state['active'] = False
                break
                
            time.sleep(0.03)  # Điều chỉnh tốc độ stream
            
        # Dọn dẹp
        cap.release()
        cv2.destroyAllWindows()
        stream_socket.close()
        update_streaming_status(server_ip, server_port, username, is_streaming=False)
        
        if streaming_state:
            streaming_state['active'] = False
        
    except Exception as e:
        logging.error(f"Error in start_stream: {e}")
        print(f"Error in start_stream: {e}")
        if streaming_state:
            streaming_state['active'] = False
        update_streaming_status(server_ip, server_port, username, is_streaming=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Node for P2P Segment Chat")
    parser.add_argument('--peer-port', type=int, default=33357, help='Port for peer server')
    parser.add_argument('--visitor', action='store_true', help='Run as visitor')
    args = parser.parse_args()
    
    peer_ip = '127.0.0.1'
    peer_port = args.peer_port
    server_ip = '127.0.0.1'
    server_port = 22236
    session_id = 'session1'
    channel_id = 'channel_1'
    
    # Kiểm tra cổng
    if not check_port(peer_ip, peer_port):
        messagebox.showerror("Error", f"Port {peer_port} is already in use. Please choose a different port.")
        sys.exit(1)
    
    # Nhập tên người dùng
    username = input("Enter your username: ").strip()
    if not username:
        username = "user1"
        
    # Kết nối với tracker
    success, message = thread_client(1, server_ip, server_port, peer_ip, peer_port, username, session_id, args.visitor)
    if not success:
        messagebox.showerror("Error", f"Failed to register: {message}")
        sys.exit(1)
    
    # Khởi động luồng lắng nghe terminal
    tinput = Thread(target=terminal_input_handler, daemon=True)
    tinput.start()
    
    # Khởi động server và UI
    tserver = Thread(target=thread_server, args=(peer_ip, peer_port))
    tserver.start()
    create_ui(username, server_ip, server_port, channel_id, args.visitor)