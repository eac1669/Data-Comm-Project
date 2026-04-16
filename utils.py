import hashlib


def hash_file(path):
    
    h = hashlib.sha256()

    with open(path, "rb") as f:
        
        while True:
            
            chunk = f.read(4096)
            
            if not chunk:
                break
            
            h.update(chunk)

    return h.hexdigest()