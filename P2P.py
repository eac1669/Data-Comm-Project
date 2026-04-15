import socket
import threading
import sys


# Track active connections (for debugging)
active_connections = 0
lock = threading.Lock()


# ----------------------------
# Server: listens for messages
# ----------------------------
def start_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"[LISTENING] Peer is listening on {host}:{port}")

    while True:
        conn, addr = server_socket.accept()

        thread = threading.Thread(
            target=handle_client,
            args=(conn, addr),
            daemon=True
        )
        thread.start()


# ----------------------------
# Handle each client (THREAD)
# ----------------------------
def handle_client(conn, addr):
    global active_connections

    with lock:
        active_connections += 1
        print(f"[NEW CONNECTION] {addr} | Active: {active_connections}")

    try:
        while True:
            message = conn.recv(1024).decode()

            if not message:
                break  # client disconnected

            print(f"[{addr}] {message}")

            response = f"ACK from {addr}"
            conn.send(response.encode())

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")

    finally:
        conn.close()

        with lock:
            active_connections -= 1
            print(f"[DISCONNECTED] {addr} | Active: {active_connections}")


# ----------------------------
# Client: one-time message
# ----------------------------
def send_message(target_host, target_port, message):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))

        client_socket.send(message.encode())
        response = client_socket.recv(1024).decode()

        print(f"[RESPONSE] {response}")

        client_socket.close()

    except Exception as e:
        print(f"[ERROR] Could not send message: {e}")


# ----------------------------
# Client: persistent connection
# ----------------------------
def interactive_client(target_host, target_port):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))

        print(f"[CONNECTED TO {target_host}:{target_port}]")

        while True:
            msg = input("Message (type 'exit' to quit): ")

            if msg.lower() == "exit":
                break

            client_socket.send(msg.encode())
            response = client_socket.recv(1024).decode()

            print(f"[RESPONSE] {response}")

        client_socket.close()
        print("[CONNECTION CLOSED]")

    except Exception as e:
        print(f"[ERROR] {e}")


# ----------------------------
# Main Peer Program
# ----------------------------
def main():
    if len(sys.argv) != 2:
        print("Usage: python peer.py <port>")
        sys.exit(1)

    host = "127.0.0.1"
    port = int(sys.argv[1])

    # Start server thread
    server_thread = threading.Thread(
        target=start_server,
        args=(host, port),
        daemon=True
    )
    server_thread.start()

    # CLI loop
    while True:
        command = input(
            "\nCommands:\n"
            "  send <ip> <port> <message>\n"
            "  connect <ip> <port>\n> "
        )

        if command.startswith("send"):
            try:
                parts = command.split()
                target_ip = parts[1]
                target_port = int(parts[2])
                message = " ".join(parts[3:])

                send_message(target_ip, target_port, message)

            except Exception:
                print("Invalid format. Example:")
                print("send 127.0.0.1 5002 Hello World!!")

        elif command.startswith("connect"):
            try:
                parts = command.split()
                target_ip = parts[1]
                target_port = int(parts[2])

                interactive_client(target_ip, target_port)

            except Exception:
                print("Usage: connect <ip> <port>")


if __name__ == "__main__":
    main()