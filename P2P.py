import socket
import threading
import sys
from protocol import encode, decode

active_connections = 0
lock = threading.Lock()


def start_server(host, port):
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"[LISTENING] Peer is listening on {host}:{port}")

    while True:
        
        conn, addr = server_socket.accept()

        thread1 = threading.Thread(
            
            target=handle_client,
            args=(conn, addr, port),
            daemon=True
        )
        thread1.start()


def handle_client(conn, addr, port):
    
    global active_connections

    with lock:
        # Active connections is used for debugging for now.
        active_connections += 1
        print(f"[NEW CONNECTION] {addr} | Active: {active_connections}")

    try:
        
        while True:
            
            data = conn.recv(4096)

            if not data:
                
                break 

            message = decode(data)
            print(f"[RECV {addr}] {message}")


            if message.get("type") == "PING":
                
                response = {"type": "PONG", "from": port}

            elif message.get("type") == "ECHO":
                
                response = {
                    "type": "ECHO_REPLY",
                    "message": message.get("message", "")
                }

            else:
                
                response = {"type": "ERROR", "message": "Unknown message type"}

            conn.send(encode(response))

    except Exception as e:
        
        print(f"[ERROR] {addr}: {e}")

    finally:
        
        conn.close()

        with lock:
            
            active_connections -= 1
            print(f"[DISCONNECTED] {addr} | Active: {active_connections}")


def send_message(target_host, target_port, message):
    
    try:
        
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))
        client_socket.send(encode(message))
        response = decode(client_socket.recv(4096))
        print(f"[RESPONSE] {response}")
        client_socket.close()

    except Exception as e:
        print(f"[ERROR] Could not send message: {e}")



def interactive_client(target_host, target_port):
    
    try:
        
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))
        print(f"[CONNECTED TO {target_host}:{target_port}]")

        while True:
            
            message = input("Message (type 'exit' to quit): ")

            if message.lower() == "exit":
                break

            request = {
                "type": "ECHO",
                "message": message
            }

            client_socket.send(encode(request))
            response = decode(client_socket.recv(4096))

            print(f"[RESPONSE] {response}")

        client_socket.close()
        print("[CONNECTION CLOSED]")

    except Exception as e:
        print(f"[ERROR] {e}")


def main():
    
    if len(sys.argv) != 2:
    
        print("Usage: python peer.py <port>")
        sys.exit(1)

    host = "127.0.0.1"
    port = int(sys.argv[1])
    server_thread = threading.Thread(
        target=start_server,
        args=(host, port),
        daemon=True
    )
    server_thread.start()

    while True:
        
        command = input(
            "\nCommands:\n"
            "  ping <ip> <port>\n"
            "  echo <ip> <port> <message>\n"
            "  connect <ip> <port>\n> "
        )

        parts = command.split()

        if not parts:
            
            continue

        try:

            if parts[0] == "ping":
                
                ip, port_ = parts[1], int(parts[2])

                send_message(ip, port_, {"type": "PING"})


            elif parts[0] == "echo":
                
                ip, port_ = parts[1], int(parts[2])
                message = " ".join(parts[3:])
                send_message(ip, port_, {
                    "type": "ECHO",
                    "message": message
                })

            elif parts[0] == "connect":
                
                ip, port_ = parts[1], int(parts[2])
                interactive_client(ip, port_)

        except Exception:
            print("Invalid command format.")


if __name__ == "__main__":
    main()