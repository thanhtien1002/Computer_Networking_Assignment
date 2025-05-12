import cv2
import numpy as np
import pickle
import socket
import time
import json
import logging
from threading import Thread
from config_manager import config
from PIL import Image, ImageTk

class VideoStream:
    def __init__(self, username):
        self.username = username
        self.window_name = None
        self.stream_socket = None
        self.cap = None
        self.is_streaming = False
        self.is_receiving = False
        self.receiving_socket = None
        self.window_created = False
        self.server_ip = None
        self.server_port = None
        self.stream_request_pending = False  # Flag cho biết có yêu cầu stream đang chờ
        self.current_stream_sender = None  # Lưu username của người đang gửi stream
        self.streaming_config = config.get_streaming_config()
        self.frame_quality = self.streaming_config.get('frame_quality', 80)
        self.frame_rate = self.streaming_config.get('frame_rate', 30)
        self.retry_count = 0
        self.max_retries = 3
        self.network_status = {
            'failed_sends': 0,
            'total_sends': 0,
            'last_quality_check': time.time()
        }
        self.status_text = ""
        self.status_color = (255, 255, 255)  # White
        self.window_size = (640, 480)
        
    def check_camera(self):
        """Kiểm tra camera có sẵn và hoạt động không"""
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return False, "Không thể mở camera"
            
            ret, frame = cap.read()
            if not ret or frame is None:
                return False, "Camera không hoạt động"
                
            cap.release()
            return True, "Camera OK"
        except Exception as e:
            return False, f"Lỗi camera: {str(e)}"

    def _update_streaming_status(self, server_ip, server_port, is_streaming=False, is_receiving=False):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(self.streaming_config.get('timeout', 2.0))
            client_socket.connect((server_ip, server_port))
            client_socket.send(json.dumps({
                'type': 'UPDATE_STREAM_STATUS',
                'username': self.username,
                'is_streaming': is_streaming,
                'is_receiving': is_receiving
            }).encode('utf-8'))
            response = json.loads(client_socket.recv(1024).decode('utf-8'))
            client_socket.close()
            return response['status'] == 'OK'
        except Exception as e:
            print(f"Error updating streaming status: {e}")
            return False

    def handle_stream_signal(self, data, addr):
        """Xử lý tín hiệu stream nhận được"""
        try:
            received_data = pickle.loads(data)
            if isinstance(received_data, dict):
                if 'stream_request' in received_data:
                    # Nhận yêu cầu bắt đầu stream
                    requester = received_data.get('requester_username', 'Unknown')
                    print(f"\nReceived stream request from {requester}")
                    self.stream_request_pending = True
                    return True
                elif 'frame' in received_data:
                    # Nhận frame video
                    sender_username = received_data.get('sender_username', 'Unknown')
                    if not self.current_stream_sender:
                        self.current_stream_sender = sender_username
                        print(f"\nStarted receiving stream from {sender_username}")
                    return False
        except:
            pass
        return False

    def _safe_destroy_window(self):
        """Hàm an toàn để đóng cửa sổ"""
        try:
            if self.window_created and self.window_name:
                cv2.destroyWindow(self.window_name)
                cv2.waitKey(100)  # Đợi lâu hơn để đảm bảo cửa sổ được đóng
                self.window_created = False
                self.window_name = None
        except Exception as e:
            print(f"Warning: Error destroying window: {e}")
        finally:
            cv2.destroyAllWindows()
            cv2.waitKey(100)

    def _safe_create_window(self, title):
        """Tạo cửa sổ với controls"""
        try:
            self._safe_destroy_window()
            
            self.window_name = title
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.window_name, *self.window_size)
            
            # Tạo trackbar để điều chỉnh kích thước
            def on_width_change(value):
                self.window_size = (value, self.window_size[1])
                cv2.resizeWindow(self.window_name, *self.window_size)
                
            def on_height_change(value):
                self.window_size = (self.window_size[0], value)
                cv2.resizeWindow(self.window_name, *self.window_size)
            
            cv2.createTrackbar('Width', self.window_name, self.window_size[0], 1920, on_width_change)
            cv2.createTrackbar('Height', self.window_name, self.window_size[1], 1080, on_height_change)
            
            self.window_created = True
            print(f"Successfully created window: {self.window_name}")
            return True
        except Exception as e:
            print(f"Warning: Could not create window: {e}")
            self.window_created = False
            self.window_name = None
            return False

    def _adjust_video_quality(self):
        """Điều chỉnh chất lượng video dựa trên tình trạng mạng"""
        if time.time() - self.network_status['last_quality_check'] < 5:
            return

        if self.network_status['total_sends'] > 0:
            failure_rate = self.network_status['failed_sends'] / self.network_status['total_sends']
            
            if failure_rate > 0.3 and self.frame_quality > 30:
                self.frame_quality = max(30, self.frame_quality - 10)
                self.frame_rate = max(15, self.frame_rate - 5)
                print(f"\nReducing video quality: Quality={self.frame_quality}, FPS={self.frame_rate}")
            elif failure_rate < 0.1 and self.frame_quality < 80:
                self.frame_quality = min(80, self.frame_quality + 5)
                self.frame_rate = min(30, self.frame_rate + 2)
                print(f"\nIncreasing video quality: Quality={self.frame_quality}, FPS={self.frame_rate}")

        self.network_status['failed_sends'] = 0
        self.network_status['total_sends'] = 0
        self.network_status['last_quality_check'] = time.time()

    def _send_frame(self, frame_data, receiver):
        """Gửi frame với retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                if self.stream_socket:
                    self.stream_socket.sendto(frame_data, (receiver['peer_ip'], receiver['peer_port']))
                    self.network_status['total_sends'] += 1
                    return True
            except Exception as e:
                print(f"Attempt {attempt + 1}/{self.max_retries} failed for {receiver['username']}: {e}")
                time.sleep(0.1)
        
        self.network_status['failed_sends'] += 1
        self.network_status['total_sends'] += 1
        return False

    def _update_status(self, text, color=(255, 255, 255)):
        """Cập nhật trạng thái hiển thị trên video"""
        self.status_text = text
        self.status_color = color

    def _draw_status_overlay(self, frame):
        """Vẽ overlay thông tin trạng thái lên frame"""
        if not self.status_text:
            return frame

        # Tạo bản sao để không ảnh hưởng đến frame gốc
        overlay = frame.copy()
        
        # Vẽ background cho text
        text_size = cv2.getTextSize(self.status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.rectangle(overlay, (10, 10), (text_size[0] + 20, 40), (0, 0, 0), -1)
        
        # Vẽ text
        cv2.putText(overlay, self.status_text, (15, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.status_color, 2)

        # Thêm FPS và quality nếu đang stream
        if self.is_streaming:
            status = f"FPS: {self.frame_rate} | Quality: {self.frame_quality}%"
            cv2.putText(overlay, status, (15, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return cv2.addWeighted(overlay, 0.8, frame, 0.2, 0)

    def start_sending(self, server_ip, server_port, streaming_state):
        try:
            camera_ok, message = self.check_camera()
            if not camera_ok:
                self._update_status(f"Camera error: {message}", (0, 0, 255))  # Red
                print(f"Camera error: {message}")
                if streaming_state:
                    streaming_state['active'] = False
                return

            if self.current_stream_sender:
                self._update_status(f"Cannot stream while receiving from {self.current_stream_sender}", (0, 255, 255))  # Yellow
                print(f"\nCannot start streaming while receiving from {self.current_stream_sender}")
                if streaming_state:
                    streaming_state['active'] = False
                return

            self.server_ip = server_ip
            self.server_port = server_port
            
            self.cleanup()
            
            if not self._update_streaming_status(server_ip, server_port, is_streaming=True, is_receiving=False):
                print("Failed to update streaming status")
                if streaming_state:
                    streaming_state['active'] = False
                return

            try:
                self.stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.stream_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception as e:
                print(f"Error creating stream socket: {e}")
                if streaming_state:
                    streaming_state['active'] = False
                return
            
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((server_ip, server_port))
                client_socket.send(json.dumps({'type': 'GET_LIST'}).encode('utf-8'))
                peers = json.loads(client_socket.recv(1024).decode('utf-8'))['peers']
                client_socket.close()
            except Exception as e:
                print(f"Error getting peer list: {e}")
                if streaming_state:
                    streaming_state['active'] = False
                return
            
            if not peers:
                print("No peers available for streaming")
                if streaming_state:
                    streaming_state['active'] = False
                return
                
            receivers = [peer for peer in peers if peer['username'] != self.username]
            if not receivers:
                print("No receivers available")
                if streaming_state:
                    streaming_state['active'] = False
                return

            try:
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    raise Exception("Cannot open camera")
            except Exception as e:
                print(f"Error opening camera: {e}")
                if streaming_state:
                    streaming_state['active'] = False
                return

            self.is_streaming = True
            streaming_state['active'] = True
            
            # Tạo cửa sổ gửi
            window_title = f"[SENDING] Your Stream ({self.username})"
            self._safe_create_window(window_title)
            
            print(f"Started streaming to {len(receivers)} peers")
            print("Press 'q' to stop streaming")
            
            frame_count = 0
            while self.cap and self.cap.isOpened() and streaming_state['active'] and self.stream_socket:
                try:
                    ret, frame = self.cap.read()
                    if not ret:
                        print("Error: Cannot read frame from camera")
                        break
                        
                    _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 
                                                           self.frame_quality])
                    frame_data = pickle.dumps({
                        'frame': buffer,
                        'sender_username': self.username,
                        'frame_count': frame_count,
                        'is_last_frame': not streaming_state['active']
                    })
                    
                    for receiver in receivers:
                        if not self._send_frame(frame_data, receiver):
                            print(f"Failed to send frame to {receiver['username']} after {self.max_retries} attempts")
                    
                    self._adjust_video_quality()
                    
                    if self.window_created:
                        try:
                            # Thêm overlay status
                            display_frame = self._draw_status_overlay(frame)
                            cv2.imshow(self.window_name, display_frame)
                            key = cv2.waitKey(1) & 0xFF
                            if key == ord('q'):
                                self._update_status("Stopping stream...", (0, 255, 255))
                                print("User requested to stop streaming")
                                break
                        except Exception as e:
                            print(f"Warning: Error displaying frame: {e}")
                            self.window_created = False
                    
                    frame_count += 1
                    time.sleep(1.0 / self.frame_rate)
                    
                except Exception as e:
                    print(f"Error in streaming loop: {e}")
                    break
                    
        except Exception as e:
            print(f"Error in start_sending: {e}")
            
        finally:
            try:
                if self.stream_socket and receivers and self.cap:
                    ret, frame = self.cap.read()
                    if ret:
                        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 
                                                               self.frame_quality])
                        last_frame_data = pickle.dumps({
                            'frame': buffer,
                            'sender_username': self.username,
                            'frame_count': frame_count,
                            'is_last_frame': True
                        })
                        
                        for receiver in receivers:
                            try:
                                self.stream_socket.sendto(last_frame_data, (receiver['peer_ip'], receiver['peer_port']))
                            except:
                                pass
                                
                        time.sleep(0.1)
            except:
                pass
                
            print("Stopping send stream...")
            if streaming_state:
                streaming_state['active'] = False
            self.cleanup()
            print("Send stream stopped")
            
            print("\nSwitching to receive mode...")
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((server_ip, server_port))
                client_socket.send(json.dumps({'type': 'GET_LIST'}).encode('utf-8'))
                peers = json.loads(client_socket.recv(1024).decode('utf-8'))['peers']
                client_socket.close()
                
                my_peer = next((peer for peer in peers if peer['username'] == self.username), None)
                if my_peer:
                    self.start_receiving(my_peer['peer_ip'], my_peer['peer_port'], server_ip, server_port)
                else:
                    print("Could not find peer information to start receiving")
            except Exception as e:
                print(f"Error switching to receive mode: {e}")
            
            self._update_streaming_status(self.server_ip, self.server_port, is_streaming=False, is_receiving=False)

    def start_receiving(self, peer_ip, peer_port, server_ip, server_port, streaming_state=None):
        try:
            self.server_ip = server_ip
            self.server_port = server_port
            
            self.cleanup()
            
            if not self._update_streaming_status(server_ip, server_port, is_streaming=False, is_receiving=True):
                print("Failed to update receiving status")
                return

            try:
                self.receiving_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.receiving_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.receiving_socket.bind((peer_ip, peer_port))
                self.receiving_socket.settimeout(self.streaming_config.get('timeout', 1.0))
            except Exception as e:
                print(f"Error creating receiving socket: {e}")
                return
            
            self.is_receiving = True
            print("\nWaiting for stream signals...")
            
            while self.is_receiving:
                try:
                    data, addr = self.receiving_socket.recvfrom(self.streaming_config.get('max_frame_size', 65507))
                    
                    is_request = self.handle_stream_signal(data, addr)
                    if is_request:
                        if not self.current_stream_sender:
                            print("Stream request received. You can start streaming.")
                            continue
                        else:
                            print(f"Cannot accept stream request while receiving from {self.current_stream_sender}")
                            continue
                            
                    try:
                        received_data = pickle.loads(data)
                        if isinstance(received_data, dict) and 'frame' in received_data:
                            frame = cv2.imdecode(np.frombuffer(received_data['frame'], np.uint8), cv2.IMREAD_COLOR)
                            sender_username = received_data.get('sender_username', 'Unknown')
                            is_last_frame = received_data.get('is_last_frame', False)
                            
                            if frame is not None:
                                if streaming_state and 'window' in streaming_state:
                                    # Hiển thị frame trong cửa sổ stream
                                    try:
                                        # Chuyển đổi frame từ BGR sang RGB
                                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                        # Chuyển đổi frame thành định dạng PIL
                                        frame_pil = Image.fromarray(frame_rgb)
                                        # Chuyển đổi frame thành định dạng PhotoImage
                                        frame_tk = ImageTk.PhotoImage(image=frame_pil)
                                        
                                        # Cập nhật label với frame mới
                                        streaming_state['label'].configure(image=frame_tk)
                                        streaming_state['label'].image = frame_tk  # Giữ tham chiếu
                                    except Exception as e:
                                        print(f"Error displaying frame in window: {e}")
                                else:
                                    # Hiển thị frame trong cửa sổ OpenCV
                                    if not self.window_created:
                                        window_title = f"[RECEIVING] Stream from {sender_username}"
                                        self._safe_create_window(window_title)
                                        
                                    if self.window_created:
                                        cv2.imshow(self.window_name, frame)
                                        key = cv2.waitKey(1) & 0xFF
                                        if key == ord('q'):
                                            print("User requested to stop receiving")
                                            break
                                    
                                if is_last_frame:
                                    print(f"\nStream from {sender_username} ended")
                                    self.current_stream_sender = None
                                    if streaming_state and 'window' in streaming_state:
                                        streaming_state['window'].destroy()
                                    else:
                                        self._safe_destroy_window()
                                    print("\nWaiting for new stream signals...")
                            
                    except Exception as e:
                        print(f"Error processing frame: {e}")
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    if "not a socket" in str(e):
                        break
                        
        except Exception as e:
            print(f"Error in start_receiving: {e}")
            
        finally:
            print("Stopping receive stream...")
            self.cleanup()
            print("Receive stream stopped")
            
    def cleanup(self):
        if self.server_ip and self.server_port:
            self._update_streaming_status(self.server_ip, self.server_port, 
                                       is_streaming=False, is_receiving=False)
        
        if self.cap is not None:
            try:
                self.cap.release()
                print("Camera released")
            except:
                pass
            self.cap = None
            
        if self.stream_socket is not None:
            try:
                self.stream_socket.close()
                print("Stream socket closed")
            except:
                pass
            self.stream_socket = None
            
        if self.receiving_socket is not None:
            try:
                self.receiving_socket.close()
                print("Receiving socket closed")
            except:
                pass
            self.receiving_socket = None
            
        self._safe_destroy_window()
            
        self.is_streaming = False
        self.is_receiving = False
        self.stream_request_pending = False
        self.current_stream_sender = None
        
        print("Cleanup completed")
        print("--------------------------------") 