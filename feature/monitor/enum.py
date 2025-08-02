from enum import Enum


class MonitorEnum(Enum):
    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def check_value_valid(cls, value) -> bool:  # noqa: ANN001
        return value in cls._value2member_map_


class TaskState(MonitorEnum):
    UNKNOWN = "unknown"
    NEWBORN = "newborn"
    WORKING = "working"
    DEATH = "death"
    DEFAULT = "default"

    _allowed_transitions = {
        (NEWBORN, WORKING),
        (WORKING, DEATH),
        (NEWBORN, DEATH),
        (DEFAULT, WORKING),  # monitor start
        (DEFAULT, NEWBORN),  # process start
    }

    @classmethod
    def check_valid_transition(cls, state: "TaskState", new_state: "TaskState") -> bool:
        return (state.value, new_state.value) in cls._allowed_transitions.value


class TaskEvent(MonitorEnum):
    UNKNOWN = "unknown"
    CREATE = "create"
    FINISH = "finish"


class MsgType(MonitorEnum):
    UNKNOWN = "unknown"
    NORMAL = "normal"
    WARNING = "warning"
    DISK_WARNING_TO_USER = "disk_warning_to_user"


class WebhookState(MonitorEnum):
    UNKNOWN = "unknown"
    WORKING = "working"
    SLEEPING = "sleeping"


class AllWebhookName(MonitorEnum):
    WEWORK = "wework"
    LARK = "lark"
    ALL = [WEWORK, LARK]
