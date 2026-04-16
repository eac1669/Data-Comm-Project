import socket
import threading
import sys

from protocol import encode, decode
from file_indexing import has_file

from file_indexing import has_file, get_file_path
from chunks import read_chunk, get_total_chunks

from utils import hash_file


TRACKER_HOST = "127.0.0.1"
TRACKER_PORT = 9000

active_connections = 0
lock = threading.Lock()


def register_with_tracker(port):
    
    try:
        
        s = socket.socket()
        s.connect((TRACKER_HOST, TRACKER_PORT))
        msg = f"REGISTER 127.0.0.1 {port}"
        s.send(msg.encode())
        print("[TRACKER]", s.recv(4096).decode())
        s.close()

    except Exception as e:
        
        print(f"[TRACKER ERROR] {e}")


def get_peers():
    
    try:
        
        s = socket.socket()
        s.connect((TRACKER_HOST, TRACKER_PORT))
        s.send("GET_PEERS".encode())
        data = s.recv(4096).decode()
        s.close()

        if data.startswith("PEERS"):
            
            peer_list = data.replace("PEERS", "").strip()

            if not peer_list:
                
                return []

            return [p.split(":") for p in peer_list.split()]

    except Exception as e:
        
        print(f"[TRACKER ERROR] {e}")

    return []


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

            elif message.get("type") == "SEARCH":

                filename = message.get("filename")

                if has_file(filename, port):
                    
                    response = {
                        "type": "FOUND",
                        "filename": filename,
                        "host": "127.0.0.1",
                        "port": port
                    }
                
                else:
                    
                    response = {
                        "type": "NOT_FOUND",
                        "filename": filename
                    }


            elif message.get("type") == "GET_FILE_INFO":

                filename = message.get("filename")

                #print(f"[DEBUG] Checking file: {filename} on port {port}")

                if has_file(filename, port):
                    
                    path = get_file_path(filename, port)
                    chunks = get_total_chunks(path)
                    file_hash = hash_file(path) 

                    response = {
                        "type": "FILE_INFO",
                        "filename": filename,
                        "chunks": chunks,
                        "hash": file_hash   
                    }

                else:
                    
                    response = {"type": "ERROR", "message": "File not found"}

            elif message.get("type") == "GET_CHUNK":

                filename = message.get("filename")
                chunk_index = message.get("chunk")

                if has_file(filename, port):
                    
                    path = get_file_path(filename, port)
                    data = read_chunk(path, chunk_index)
                    response = {
                        "type": "CHUNK_DATA",
                        "filename": filename,
                        "chunk": chunk_index,
                        "data": data.hex() 
                    }
                
                else:
                    response = {"type": "ERROR", "message": "File not found"}

            else:
                
                response = {
                    "type": "ERROR",
                    "message": "Unknown message type"
                }

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

        if response.get("type") == "FOUND":
            
            print(f"[FOUND] {response['filename']} at {response['host']}:{response['port']}")
        
        else:
            
            print(f"[RESPONSE] {response}")

        client_socket.close()

    except Exception as e:
        print(f"[ERROR] Could not send message: {e}")



def search_network(filename, self_port):

    peers = get_peers()

    if not peers:
        
        print("[INFO] No peers found from tracker")
        return

    print(f"[INFO] Searching for '{filename}' across peers...")

    for ip, port in peers:
        
        port = int(port)

        if port == self_port:
            
            continue

        send_message(ip, port, {
            "type": "SEARCH",
            "filename": filename
        })


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


def download_file(filename, peer_ip, peer_port, self_port):

    from file_indexing import get_shared_folder
    from utils import hash_file
    import socket

    client_socket = socket.socket()
    client_socket.connect((peer_ip, peer_port))
    client_socket.send(encode({
        "type": "GET_FILE_INFO",
        "filename": filename
    }))

    response = decode(client_socket.recv(4096))
    client_socket.close()

    if response.get("type") != "FILE_INFO":
        
        print("[ERROR] Could not get file info")
        return

    total_chunks = response["chunks"]
    expected_hash = response["hash"]
    print(f"[INFO] Downloading {filename} ({total_chunks} chunks)")
    chunks = []

    for i in range(total_chunks):

        try:
            
            s = socket.socket()
            s.connect((peer_ip, peer_port))
            s.send(encode({
                "type": "GET_CHUNK",
                "filename": filename,
                "chunk": i
            }))

            chunk_response = decode(s.recv(4096))
            s.close()

            if chunk_response.get("type") != "CHUNK_DATA":
                
                print(f"[ERROR] Failed chunk {i}")
                continue

            #data = bytes.fromhex(chunk_response["data"])
            #if i == 2:
            #    data = b"CORRUPTED_DATA"  
            
            data = bytes.fromhex(chunk_response["data"])
            chunks.append((i, data))
            print(f"[DOWNLOADED] chunk {i}")

        except Exception as e:
            
            print(f"[ERROR] chunk {i}: {e}")

    chunks.sort(key=lambda x: x[0])
    save_path = f"{get_shared_folder(self_port)}/{filename}"

    with open(save_path, "wb") as f:
        for _, data in chunks:
            f.write(data)

    print(f"[INFO] File saved to {save_path}")
    downloaded_hash = hash_file(save_path)

    #print(f"[DEBUG] Expected hash:  {expected_hash}")
    #print(f"[DEBUG] Actual hash:    {downloaded_hash}")

    if downloaded_hash == expected_hash:
        
        print("[SUCCESS] File integrity VERIFIED ✅")
    
    else:
        
        print("[ERROR] File CORRUPTED ❌")


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

    register_with_tracker(port)

    while True:

        command = input(
            "\nCommands:\n"
            "  ping <ip> <port>\n"
            "  echo <ip> <port> <message>\n"
            "  search <filename>\n"
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

            elif parts[0] == "search":
                
                filename = " ".join(parts[1:])
                search_network(filename, port)

            elif parts[0] == "connect":
                
                ip, port_ = parts[1], int(parts[2])
                interactive_client(ip, port_)

            elif parts[0] == "download":

                filename = parts[1]
                ip = parts[2]
                port_ = int(parts[3])
                download_file(filename, ip, port_, port)

        except Exception:
            
            print("Invalid command format.")


if __name__ == "__main__":
    main()