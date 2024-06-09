from enum import Enum


class ProgramEnum(Enum):
    def __str__(self):
        return str(self.value)


class TaskState(ProgramEnum):
    NEWBORN = "newborn"
    WORKING = "working"
    DEATH = "death"
    DEFAULT = "default"


class TaskEvent(ProgramEnum):
    CREATE = "create"
    FINISH = "finish"


class MsgType(ProgramEnum):
    NORMAL = "normal"
    WARNING = "warning"


class WebhookState(ProgramEnum):
    WORKING = "working"
    SLEEPING = "sleeping"


class AllWebhookName(ProgramEnum):
    WEWORK = "wework"
    LARK = "lark"
    ALL = [WEWORK, LARK]


if __name__ == "__main__":
    print(str(AllWebhookName.WEWORK))
    print(str(AllWebhookName.LARK))
    print(str(AllWebhookName.ALL))
