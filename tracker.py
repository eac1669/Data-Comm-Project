import socket
import threading

peers = []
lock = threading.Lock()


def handle_client(conn, addr):
    
    global peers

    try:
        data = conn.recv(4096).decode()
        parts = data.split()
        command = parts[0]

        if command == "REGISTER":
            
            ip = parts[1]
            port = int(parts[2])

            with lock:
                
                if (ip, port) not in peers:
                    
                    peers.append((ip, port))

            conn.send(f"REGISTERED {ip}:{port}".encode())

        elif command == "GET_PEERS":
            
            with lock:
                
                response = "PEERS " + " ".join([f"{ip}:{port}" for ip, port in peers])

            conn.send(response.encode())

    except Exception as e:
        
        conn.send(f"ERROR {e}".encode())

    finally:
        
        conn.close()


def start_tracker(host="127.0.0.1", port=9000):
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[TRACKER RUNNING] {host}:{port}")

    while True:
        conn, addr = server.accept()

        threading.Thread(
            target=handle_client,
            args=(conn, addr),
            daemon=True
        ).start()


if __name__ == "__main__":
    start_tracker()