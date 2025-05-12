import os
import sys
import ctypes
from ui.login_window import LoginWindow

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    # Kiểm tra nếu chưa chạy với quyền admin thì yêu cầu
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
        
    # Chạy giao diện đăng nhập
    login_window = LoginWindow()
    login_window.run() 