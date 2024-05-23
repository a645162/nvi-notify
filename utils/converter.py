def convert_bytes_to_mb(bytes: int) -> int:
    return bytes // (1024**2)

def convert_bytes_to_gb(bytes: int) -> float:
    return bytes / (1024**3)

def get_human_str_from_byte(memory_byte: int) -> str:
    memory_mb = convert_bytes_to_mb(memory_byte)
    if memory_mb < 1000:
        return f"{memory_mb}MB"
    return f"{memory_mb / 1024:.2f}GB"
