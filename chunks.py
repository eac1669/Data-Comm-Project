CHUNK_SIZE = 1024  


def get_file_size(filepath):
    
    import os
    return os.path.getsize(filepath)


def get_total_chunks(filepath):
    
    size = get_file_size(filepath)
    return (size + CHUNK_SIZE - 1) // CHUNK_SIZE


def read_chunk(filepath, chunk_index):
    
    with open(filepath, "rb") as f:
        
        f.seek(chunk_index * CHUNK_SIZE)
        return f.read(CHUNK_SIZE)