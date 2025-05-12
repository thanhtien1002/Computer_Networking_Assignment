import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os
from config_manager import config
from database import add_info, check_username_exist, check_password

class LoginWindow:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Segment Chat - Login")
        self.root.geometry("400x600")
        
        # Thiết lập theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Tạo frame chính
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Tiêu đề
        title_label = ctk.CTkLabel(
            main_frame,
            text="Segment Chat",
            font=("Roboto", 24, "bold")
        )
        title_label.pack(pady=20)
        
        # Frame cho form đăng nhập/đăng ký
        self.form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Username
        username_label = ctk.CTkLabel(self.form_frame, text="Username:")
        username_label.pack(pady=(0, 5))
        self.username_entry = ctk.CTkEntry(self.form_frame, width=200)
        self.username_entry.pack(pady=(0, 10))
        
        # Password
        password_label = ctk.CTkLabel(self.form_frame, text="Password:")
        password_label.pack(pady=(0, 5))
        self.password_entry = ctk.CTkEntry(self.form_frame, width=200, show="*")
        self.password_entry.pack(pady=(0, 10))
        
        # Server IP
        server_ip_label = ctk.CTkLabel(self.form_frame, text="Server IP:")
        server_ip_label.pack(pady=(0, 5))
        self.server_ip_entry = ctk.CTkEntry(self.form_frame, width=200)
        self.server_ip_entry.insert(0, "127.0.0.1")  # IP mặc định
        self.server_ip_entry.pack(pady=(0, 10))
        
        # Peer IP
        peer_ip_label = ctk.CTkLabel(self.form_frame, text="Your IP:")
        peer_ip_label.pack(pady=(0, 5))
        self.peer_ip_entry = ctk.CTkEntry(self.form_frame, width=200)
        self.peer_ip_entry.insert(0, "127.0.0.1")  # IP mặc định
        self.peer_ip_entry.pack(pady=(0, 10))
        
        # Mode selection
        self.mode_var = tk.StringVar(value="normal")
        mode_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        mode_frame.pack(pady=10)
        
        ctk.CTkRadioButton(
            mode_frame,
            text="Normal Mode",
            variable=self.mode_var,
            value="normal"
        ).pack(side=tk.LEFT, padx=10)
        
        ctk.CTkRadioButton(
            mode_frame,
            text="Visitor Mode",
            variable=self.mode_var,
            value="visitor"
        ).pack(side=tk.LEFT, padx=10)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        buttons_frame.pack(pady=20)
        
        # Login button
        login_button = ctk.CTkButton(
            buttons_frame,
            text="Login",
            command=self.login,
            height=40,
            font=("Roboto", 14, "bold")
        )
        login_button.pack(side=tk.LEFT, padx=10)
        
        # Register button
        register_button = ctk.CTkButton(
            buttons_frame,
            text="Register",
            command=self.show_register_dialog,
            height=40,
            font=("Roboto", 14, "bold"),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30")
        )
        register_button.pack(side=tk.LEFT, padx=10)

        # Direct Access button
        direct_access_button = ctk.CTkButton(
            main_frame,
            text="Direct Access as Visitor",
            command=self.direct_access,
            height=40,
            font=("Roboto", 14, "bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        direct_access_button.pack(pady=10)
        
        # Load cấu hình đã lưu
        self.load_config()
        
    def load_config(self):
        config_file = "login_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    saved_config = json.load(f)
                    self.username_entry.insert(0, saved_config.get("username", ""))
                    self.server_ip_entry.delete(0, tk.END)
                    self.server_ip_entry.insert(0, saved_config.get("server_ip", "127.0.0.1"))
                    self.peer_ip_entry.delete(0, tk.END)
                    self.peer_ip_entry.insert(0, saved_config.get("peer_ip", "127.0.0.1"))
            except:
                pass
                
    def save_config(self):
        config_file = "login_config.json"
        config = {
            "username": self.username_entry.get(),
            "server_ip": self.server_ip_entry.get(),
            "peer_ip": self.peer_ip_entry.get()
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
            
    def show_register_dialog(self):
        # Tạo cửa sổ đăng ký
        register_window = ctk.CTkToplevel(self.root)
        register_window.title("Register")
        register_window.geometry("400x600")
        
        # Frame chính
        main_frame = ctk.CTkFrame(register_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Tiêu đề
        title_label = ctk.CTkLabel(
            main_frame,
            text="Create Account",
            font=("Roboto", 20, "bold")
        )
        title_label.pack(pady=20)
        
        # Username
        username_label = ctk.CTkLabel(main_frame, text="Username:")
        username_label.pack(pady=(0, 5))
        username_entry = ctk.CTkEntry(main_frame, width=200)
        username_entry.pack(pady=(0, 10))
        
        # Password
        password_label = ctk.CTkLabel(main_frame, text="Password:")
        password_label.pack(pady=(0, 5))
        password_entry = ctk.CTkEntry(main_frame, width=200, show="*")
        password_entry.pack(pady=(0, 10))
        
        # Confirm Password
        confirm_label = ctk.CTkLabel(main_frame, text="Confirm Password:")
        confirm_label.pack(pady=(0, 5))
        confirm_entry = ctk.CTkEntry(main_frame, width=200, show="*")
        confirm_entry.pack(pady=(0, 10))

        # Port
        port_label = ctk.CTkLabel(main_frame, text="Port (number):")
        port_label.pack(pady=(0, 5))
        port_entry = ctk.CTkEntry(main_frame, width=200)
        port_entry.insert(0, "33357")  # Port mặc định
        port_entry.pack(pady=(0, 10))
        
        # Peer IP
        peer_ip_label = ctk.CTkLabel(main_frame, text="Your IP:")
        peer_ip_label.pack(pady=(0, 5))
        peer_ip_entry = ctk.CTkEntry(main_frame, width=200)
        peer_ip_entry.insert(0, "127.0.0.1")  # IP mặc định
        peer_ip_entry.pack(pady=(0, 10))
        
        def register():
            try:
                username = username_entry.get().strip()
                password = password_entry.get()
                confirm = confirm_entry.get()
                port_str = port_entry.get().strip()
                peer_ip = peer_ip_entry.get().strip()
                
                if not username or not password or not port_str or not peer_ip:
                    messagebox.showerror("Error", "Please fill in all fields")
                    return
                    
                if password != confirm:
                    messagebox.showerror("Error", "Passwords do not match")
                    return
                
                # Kiểm tra port là số nguyên hợp lệ
                try:
                    port = int(port_str)
                    if port <= 0 or port > 65535:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Error", "Port must be a number between 1 and 65535")
                    return
                
                # Kiểm tra username đã tồn tại
                if check_username_exist(username):
                    messagebox.showerror("Error", "Username already exists")
                    return
                    
                # Thêm user mới
                try:
                    add_info(
                        peer_ip,
                        port,
                        username,
                        password
                    )
                    messagebox.showinfo("Success", "Registration successful!")
                    register_window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Registration failed: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        # Register button
        register_button = ctk.CTkButton(
            main_frame,
            text="Register",
            command=register,
            height=40,
            font=("Roboto", 14, "bold")
        )
        register_button.pack(pady=20)
            
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        server_ip = self.server_ip_entry.get().strip()
        peer_ip = self.peer_ip_entry.get().strip()
        is_visitor = self.mode_var.get() == "visitor"
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return
            
        if not server_ip or not peer_ip:
            messagebox.showerror("Error", "Please enter valid IP addresses")
            return
            
        # Kiểm tra đăng nhập
        stored_password = check_password(username)
        if not stored_password or stored_password != password:
            messagebox.showerror("Error", "Invalid username or password")
            return
            
        # Lưu cấu hình
        self.save_config()
        
        # Đóng cửa sổ đăng nhập
        self.root.destroy()
        
        # Chạy ứng dụng với các tham số
        import subprocess
        args = [
            "python", "main.py",
            "--server-ip", server_ip,
            "--peer-ip", peer_ip
        ]
        if is_visitor:
            args.append("--visitor")
            
        # Truyền username qua stdin
        process = subprocess.Popen(args, stdin=subprocess.PIPE)
        process.communicate(input=username.encode())
        
    def direct_access(self):
        """Truy cập trực tiếp với tư cách visitor"""
        server_ip = self.server_ip_entry.get().strip()
        peer_ip = self.peer_ip_entry.get().strip()
        
        if not server_ip or not peer_ip:
            messagebox.showerror("Error", "Please enter valid IP addresses")
            return
            
        # Tạo username ngẫu nhiên cho visitor
        import random
        import string
        visitor_username = f"visitor_{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"
        
        # Đóng cửa sổ đăng nhập
        self.root.destroy()
        
        # Chạy ứng dụng với các tham số
        import subprocess
        args = [
            "python", "main.py",
            "--server-ip", server_ip,
            "--peer-ip", peer_ip,
            "--visitor"
        ]
            
        # Truyền username qua stdin
        process = subprocess.Popen(args, stdin=subprocess.PIPE)
        process.communicate(input=visitor_username.encode())
        
    def run(self):
        self.root.mainloop()