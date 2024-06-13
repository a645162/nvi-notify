import hashlib


def get_md5_hash(input: str) -> str:
    md5_hash = hashlib.md5(input.encode("utf-8"))
    return md5_hash.hexdigest()
