# -*- coding: utf-8 -*-

def get_human_str_from_byte(memory_byte: int) -> str:
    memory_mb = memory_byte / 1024 / 1024
    if memory_mb < 1024:
        return f"{memory_mb:.2f} MB"
    return f"{memory_mb / 1024:.2f} GB"
