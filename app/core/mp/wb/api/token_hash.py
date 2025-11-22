from hashlib import sha256


def get_token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()