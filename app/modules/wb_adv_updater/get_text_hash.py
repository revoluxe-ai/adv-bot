import hashlib


def get_text_hash(text):
    hash_text = hashlib.md5(text.encode()).hexdigest()
    return hash_text