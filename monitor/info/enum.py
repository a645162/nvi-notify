from enum import Enum


class TaskState(Enum):
    NEWBORN = "newborn"
    WORKING = "working"
    DEATH = "death"


class TaskEvent(Enum):
    CREATE = "create"
    FINISH = "finish"


class MsgType(Enum):
    NORMAL = "normal"
    WARNING = "warning"


class WebhookState(Enum):
    WORKING = "working"
    SLEEPING = "sleeping"


class AllWebhookName(Enum):
    WEWORK = "wework"
    LARK = "lark"
    ALL = [WEWORK, LARK]
