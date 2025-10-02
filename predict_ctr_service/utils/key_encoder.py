from urllib.parse import quote

def encode_key(raw_key: str) -> str:
    return quote(raw_key)

