from enum import Enum


class TaskState(Enum):
    NEWBORN = "newborn"
    WORKING = "working"
    DEATH = "death"
    DEFAULT = "default"


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

    def __str__(self):
        return str(self.value)


if __name__ == "__main__":
    print(str(AllWebhookName.WEWORK))
    print(str(AllWebhookName.LARK))
    print(str(AllWebhookName.ALL))
