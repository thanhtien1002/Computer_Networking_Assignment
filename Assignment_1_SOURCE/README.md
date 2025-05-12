# P2P Segment Chat

Ứng dụng chat và stream video P2P với khả năng hoạt động giữa nhiều máy tính khác nhau.

## Cấu trúc thư mục

```
.
├── config.json           # File cấu hình
├── config_manager.py     # Module quản lý cấu hình
├── main.py              # Chương trình chính cho peer
├── node.py              # Module xử lý kết nối peer
├── tracker.py           # Server tracker
├── streaming/           # Thư mục chứa các module stream
│   └── video_stream.py  # Module xử lý stream video
└── ui/                  # Thư mục chứa giao diện
    └── chat_window.py   # Module giao diện chat
```

## Cài đặt

1. Cài đặt các thư viện cần thiết:
```bash
pip install flask opencv-python numpy customtkinter
pip install pygame emoji Pillow
pip install ttkbootstrap
pip install pywin32
pip install winshell
```

2. Cấu hình trong file `config.json`:
```json
{
    "tracker": {
        "host": "0.0.0.0",      # IP của tracker server
        "socket_port": 22236,   # Port cho socket server
        "flask_port": 5000      # Port cho Flask server
    },
    "peer": {
        "default_peer_port": 33357,  # Port mặc định cho peer
        "default_username": "user1", # Tên người dùng mặc định
        "default_channel_id": "channel_1",
        "default_session_id": "session1"
    },
    "streaming": {
        "frame_quality": 80,    # Chất lượng frame (0-100)
        "frame_rate": 30,       # Tốc độ khung hình
        "timeout": 3.0,         # Thời gian chờ timeout
        "max_frame_size": 65507 # Kích thước frame tối đa
    },
    "logging": {
        "level": "INFO",        # Mức độ logging
        "max_lines": 10000      # Số dòng tối đa trong log file
    }
}
```

## Cách sử dụng

1. Chạy tracker server (trên máy chủ):
```bash
python tracker.py
```

2. Chạy peer client (trên máy khách):
```bash
python main.py --server-ip <IP_MÁY_CHỦ> --peer-ip <IP_MÁY_KHÁCH> --peer-port <PORT_MÁY_KHÁCH>
```

Ví dụ:
# HCMUT ip Wifi 703H6 192.168.110.142

```bash
# Trên máy chủ (IP: 192.168.1.100)
python tracker.py

# Trên máy khách 1 (IP: 192.168.1.101)
python main.py --server-ip 192.168.1.100 --peer-ip 192.168.1.101 --peer-port 33357

# Trên máy khách 2 (IP: 192.168.1.102)
python main.py --server-ip 192.168.1.100 --peer-ip 192.168.1.102 --peer-port 33358
```

## Tính năng

- Chat text giữa các peer
- Stream video P2P
- Tự động phát hiện và kết nối với các peer khác

## Lưu ý

1. Đảm bảo các port cần thiết được mở trên firewall:
   - Port tracker server (mặc định: 22236, 5000)
   - Port peer (mặc định: 33357)

2. Cả hai máy phải trong cùng một mạng LAN hoặc có thể kết nối với nhau qua internet

3. Nếu sử dụng NAT, cần cấu hình port forwarding trên router

4. Đảm bảo camera hoạt động nếu muốn sử dụng tính năng stream video

## Xử lý lỗi

1. Không kết nối được:
   - Kiểm tra IP và port có chính xác không
   - Kiểm tra firewall có chặn kết nối không
   - Kiểm tra các port có bị sử dụng bởi ứng dụng khác không

2. Stream video không hoạt động:
   - Kiểm tra camera có hoạt động không
   - Kiểm tra băng thông mạng
   - Kiểm tra các port UDP có được mở không

3. Lỗi kết nối giữa các peer:
   - Kiểm tra cấu hình NAT
   - Kiểm tra kết nối mạng
   - Kiểm tra log file để biết thêm chi tiết 