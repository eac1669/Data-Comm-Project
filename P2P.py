import socket
import threading
import sys
import time

from protocol import encode, decode
from file_indexing import has_file, get_file_path, get_shared_folder
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

        threading.Thread(
            target=handle_client,
            args=(conn, addr, port),
            daemon=True
        ).start()


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
                
                time.sleep(7)
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

                if has_file(filename, port):
                    
                    path = get_file_path(filename, port)
                    chunk_count = get_total_chunks(path)
                    file_hash = hash_file(path)
                    response = {
                        "type": "FILE_INFO",
                        "filename": filename,
                        "chunks": chunk_count,
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


                    #if chunk_index == 2:
                    #    data = b"CORRUPTED_DATA"


                    response = {
                        "type": "CHUNK_DATA",
                        "filename": filename,
                        "chunk": chunk_index,
                        "data": data.hex()
                    }
                else:
                    
                    response = {"type": "ERROR", "message": "File not found"}

            else:
                
                response = {"type": "ERROR", "message": "Unknown message type"}

            conn.send(encode(response))

    finally:
        
        conn.close()

        with lock:
            
            active_connections -= 1
            print(f"[DISCONNECTED] {addr} | Active: {active_connections}")


def send_message(target_host, target_port, message):
    
    try:
        
        s = socket.socket()
        s.connect((target_host, target_port))
        s.send(encode(message))
        response = decode(s.recv(4096))
        s.close()

        return response

    except Exception as e:
        
        print(f"[ERROR] Could not send message: {e}")
        return None

def download_file(filename, peer_ip, peer_port, self_port):

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

    results = {}
    thread_lock = threading.Lock()

    def download_chunk(i):
        
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
                
                print(f"[ERROR] chunk {i} failed")
                return

            data = bytes.fromhex(chunk_response["data"])

            
            #if i == 2:
            #    print("[TEST] Corrupting chunk 2")
            #    data = b"CORRUPTED_DATA"

            
            with thread_lock:
                
                results[i] = data

            print(f"[DOWNLOADED] chunk {i}")

        except Exception as e:
            
            print(f"[ERROR] chunk {i}: {e}")

    threads = []

    for i in range(total_chunks):
        
        t = threading.Thread(target=download_chunk, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        
        t.join()

    save_path = f"{get_shared_folder(self_port)}/{filename}"

    with open(save_path, "wb") as f:
        
        for i in range(total_chunks):
            
            if i in results:
                
                f.write(results[i])

    print(f"[INFO] File saved to {save_path}")

    downloaded_hash = hash_file(save_path)

    if downloaded_hash == expected_hash:
        
        print("[SUCCESS] File integrity VERIFIED")
    
    else:
        
        print("[ERROR] File CORRUPTED")


def search_network(filename, self_port):
    
    peers = get_peers()

    if not peers:
        
        print("[INFO] No peers found from tracker")
        return

    print(f"[INFO] Searching for '{filename}' across peers...")
    found = False

    for ip, port in peers:
        
        port = int(port)

        if port == self_port:
            
            continue

        response = send_message(ip, port, {
            "type": "SEARCH",
            "filename": filename
        })

        if response and response.get("type") == "FOUND":
            
            print(f"[FOUND] {filename} at {response['host']}:{response['port']}")
            found = True
            break

    if not found:
        
        print(f"[NOT FOUND] {filename} not found in network")

def interactive_client(target_host, target_port):
    
    try:
        
        s = socket.socket()
        s.connect((target_host, target_port))
        print(f"[CONNECTED TO {target_host}:{target_port}]")

        while True:
            
            msg = input("> ")

            if msg.lower() == "exit":
                
                break

            s.send(encode({
                "type": "ECHO",
                "message": msg
            }))

            print(decode(s.recv(4096)))

        s.close()

    except Exception as e:
        
        print(f"[ERROR] {e}")


def main():
    
    if len(sys.argv) != 2:
        
        print("Usage: python peer.py <port>")
        return

    host = "127.0.0.1"
    port = int(sys.argv[1])

    threading.Thread(
        target=start_server,
        args=(host, port),
        daemon=True
    ).start()

    register_with_tracker(port)

    while True:
        
        command = input("\n> ").split()

        if not command:
            
            continue

        try:
            
            if command[0] == "ping":
                
                send_message(command[1], int(command[2]), {"type": "PING"})

            elif command[0] == "echo":
                
                send_message(command[1], int(command[2]), {
                    "type": "ECHO",
                    "message": " ".join(command[3:])
                })

            elif command[0] == "search":
                
                search_network(" ".join(command[1:]), port)

            elif command[0] == "connect":
                
                interactive_client(command[1], int(command[2]))

            elif command[0] == "download":
                
                download_file(command[1], command[2], int(command[3]), port)

        except Exception:
            
            print("Invalid command format.")


if __name__ == "__main__":
    main()