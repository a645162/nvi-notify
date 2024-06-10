from enum import Enum


class MonitorEnum(Enum):
    def __str__(self):
        return str(self.value)


class TaskState(MonitorEnum):
    NEWBORN = "newborn"
    WORKING = "working"
    DEATH = "death"
    DEFAULT = "default"


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


if __name__ == "__main__":
    print(str(AllWebhookName.WEWORK))
    print(str(AllWebhookName.LARK))
    print(str(AllWebhookName.ALL))
