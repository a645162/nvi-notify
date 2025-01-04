class Converter:
    @staticmethod
    def convert_bytes_to_mb(bytes: int) -> int:
        return bytes >> 20

    @staticmethod
    def convert_mb_to_bytes(mb: int) -> int:
        return mb << 20

    @staticmethod
    def convert_bytes_to_gb(bytes: int) -> int:
        return bytes >> 30

    @staticmethod
    def convert_gb_to_bytes(gb: int) -> int:
        return gb << 30

    @staticmethod
    def convert_bytes_to_tb(bytes: int) -> int:
        return bytes >> 40

    @staticmethod
    def convert_tb_to_bytes(tb: int) -> int:
        return tb << 40
