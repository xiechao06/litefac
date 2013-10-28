# -*- coding: utf-8 -*-

STATUS_LOADING = 1
STATUS_WEIGHING = 2
STATUS_CLOSED = 3
STATUS_DISMISSED = 4

ACT_LOAD = 1
ACT_WEIGHT = 2
ACT_CLOSE = 3
ACT_OPEN = 4
ACT_DISMISS = 5


def desc_action(action):
    if action == ACT_LOAD:
        return u"卸货"
    elif action == ACT_WEIGHT:
        return u"称重"
    elif action == ACT_CLOSE:
        return u"关闭"
    elif action == ACT_OPEN:
        return u"打开"
    return "未知"

g_status_desc = {
    STATUS_LOADING: u"正在卸货",
    STATUS_WEIGHING: u"等待称重",
    STATUS_CLOSED: u"关闭",
    STATUS_DISMISSED: u"取消",
}

def desc_status(status):
    return g_status_desc.get(status, u"未知状态")


