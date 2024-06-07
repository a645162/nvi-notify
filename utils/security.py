import hashlib


def get_md5_hash(input: str) -> str:
    md5_hash = hashlib.md5(input.encode('utf-8'))
    return md5_hash.hexdigest()


if __name__ == "__main__":
    # 使用函数计算 "test" 的 MD5 哈希值
    md5_result = get_md5_hash("test")
    print(md5_result)
