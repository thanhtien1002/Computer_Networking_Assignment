# backend/app/tracker.py
import socket
import json
import threading

peer_list = []

def handle_connection(conn, addr):
    with conn:
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break
                request = json.loads(data)
                if request["command"] == "submit_info":
                    peer_list.append({"ip": request["ip"], "port": request["port"]})
                    conn.send(json.dumps({"status": "success"}).encode())
                    # Ghi log
                    with open("connection.log", "a") as f:
                        f.write(f"Peer connected: {addr} -> Tracker\n")
                elif request["command"] == "get_list":
                    conn.send(json.dumps({"peers": peer_list}).encode())
            except:
                print(f"Error with {addr}")
                break

def tracker_server():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind(("127.0.0.1", 22236))
    serversocket.listen(10)
    print("Tracker listening on 127.0.0.1:22236")
    while True:
        conn, addr = serversocket.accept()
        threading.Thread(target=handle_connection, args=(conn, addr)).start()

if __name__ == "__main__":
    tracker_server()