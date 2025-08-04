from nvi_notify.base.enums import EnumBase


class WebhookState(EnumBase):
    UNKNOWN = "unknown"
    WORKING = "working"
    SLEEPING = "sleeping"


class AllWebhookName(EnumBase):
    WEWORK = "wework"
    LARK = "lark"
    ALL = [WEWORK, LARK]
