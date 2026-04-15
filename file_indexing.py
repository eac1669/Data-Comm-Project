import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_shared_folder(port):
    
    return os.path.join(BASE_DIR, f"shared_{port}")


def list_files(port):
    
    folder = get_shared_folder(port)
    os.makedirs(folder, exist_ok=True)
    return os.listdir(folder)


def has_file(filename, port):
    
    return filename in list_files(port)