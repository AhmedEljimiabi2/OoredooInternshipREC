import socket
import threading
import json

HOST = "0.0.0.0"
PORT = 5000

def handle_client(conn, addr):
    print(f"[CONNECTED] {addr}")

    while True:
        try:
            data = conn.recv(4096)

            if not data:
                break

            message = data.decode("utf-8")
            device_data = json.loads(message)

            print("\n--- Device Data ---")
            print(f"Device Name: {device_data['device_name']}")
            print(f"IP Address: {device_data['ip']}")
            print(f"CPU: {device_data['cpu']}%")
            print(f"Memory: {device_data['memory']}%")
            print(f"Disk: {device_data['disk']}%")

        except Exception as e:
            print(f"[ERROR] {e}")
            break

    conn.close()
    print(f"[DISCONNECTED] {addr}")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print(f"[SERVER STARTED] Listening on port {PORT}")

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()
    print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")