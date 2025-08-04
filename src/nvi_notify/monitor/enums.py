from nvi_notify.base.enums import EnumBase


class TaskState(EnumBase):
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


class TaskEvent(EnumBase):
    UNKNOWN = "unknown"
    CREATE = "create"
    FINISH = "finish"


class MsgType(EnumBase):
    UNKNOWN = "unknown"
    NORMAL = "normal"
    WARNING = "warning"
    DISK_WARNING_TO_USER = "disk_warning_to_user"
