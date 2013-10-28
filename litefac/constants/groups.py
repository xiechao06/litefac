# -*- coding: utf-8 -*-
"""
基本的用户角色
"""

DEPARTMENT_LEADER = 1 #: 车间主任
TEAM_LEADER = 2 #: 班组长
LOADER = 3 #: 装卸工
QUALITY_INSPECTOR = 4 #: 质检员
CARGO_CLERK = 5 #: 收发员
SCHEDULER = 6 #: 调度员
ACCOUNTANT = 7 #: 财会人员
ADMINISTRATOR = 8 #: 管理员

GROUP_NAME_LIST = {DEPARTMENT_LEADER: u"车间主任",
                   TEAM_LEADER: u"班组长",
                   LOADER: u"装卸工",
                   QUALITY_INSPECTOR: u"质检员",
                   CARGO_CLERK: u"收发员",
                   SCHEDULER: u"调度员",
                   ACCOUNTANT: u"财会人员",
                   ADMINISTRATOR: u"管理员"}
