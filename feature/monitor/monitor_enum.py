from enum import Enum


class MonitorEnum(Enum):
    def __str__(self):
        return str(self.value)


class TaskState(MonitorEnum):
    NEWBORN = "newborn"
    WORKING = "working"
    DEATH = "death"
    DEFAULT = "default"

    @classmethod
    def is_valid_transition(cls, state, new_state) -> bool:
        allowed_transitions = [
            (cls.DEFAULT, cls.WORKING),  # monitor start
            (cls.DEFAULT, cls.NEWBORN),  # process start
            (cls.NEWBORN, cls.WORKING),
            (cls.WORKING, cls.DEATH),
            (cls.NEWBORN, cls.DEATH),
        ]
        return (state, new_state) in allowed_transitions


class TaskEvent(MonitorEnum):
    CREATE = "create"
    FINISH = "finish"


class MsgType(MonitorEnum):
    NORMAL = "normal"
    WARNING = "warning"


class WebhookState(MonitorEnum):
    WORKING = "working"
    SLEEPING = "sleeping"


class AllWebhookName(MonitorEnum):
    WEWORK = "wework"
    LARK = "lark"
    ALL = [WEWORK, LARK]
