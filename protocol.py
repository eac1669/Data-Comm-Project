import json

def encode(message: dict) -> bytes:

    return json.dumps(message).encode()


def decode(message_bytes: bytes) -> dict:

    return json.loads(message_bytes.decode())