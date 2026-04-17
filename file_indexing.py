import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_shared_folder(port):
    
    folder = os.path.join(BASE_DIR, f"shared_{port}")
    os.makedirs(folder, exist_ok=True)
    return folder


def get_file_path(filename, port):
    
    return os.path.join(get_shared_folder(port), filename)


def has_file(filename, port):
    
    return os.path.exists(get_file_path(filename, port))