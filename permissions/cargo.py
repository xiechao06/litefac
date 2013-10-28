# -*- coding: utf-8 -*-
"""
针对装卸货流程的权限管理
"""
from collections import namedtuple
from flask.ext.principal import Permission

UnloadSessionManagement = namedtuple("user", ["method"])

# 针对班组长的管理权限
EditUnloadSession = UnloadSessionManagement("edit_unload_session")
NewUnloadSession = UnloadSessionManagement("new_unload_session")

edit_us = Permission(EditUnloadSession)
edit_us.brief = u"修改卸货会话的权限"

new_us = Permission(NewUnloadSession)
new_us.brief = u"创建卸货会话的权限"
