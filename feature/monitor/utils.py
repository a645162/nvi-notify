class Converter:
    @staticmethod
    def convert_bytes_to_mb(bytes: int) -> int:
        return bytes // (1024**2)

    @staticmethod
    def convert_bytes_to_gb(bytes: int) -> float:
        return bytes / (1024**3)
