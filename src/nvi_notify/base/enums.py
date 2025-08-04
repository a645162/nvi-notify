from enum import Enum


class EnumBase(Enum):
    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def check_value_valid(cls, value) -> bool:  # noqa: ANN001
        return value in cls._value2member_map_
