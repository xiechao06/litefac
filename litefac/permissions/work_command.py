# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
from collections import namedtuple
from flask.ext.principal import Permission

WorkCommandManagement = namedtuple("work_command", ["method"])

ViewWorkCommand = WorkCommandManagement("view_work_command")
ScheduleWorkCommand = WorkCommandManagement("schedule_work_command")

view_work_command = Permission(ViewWorkCommand)
view_work_command.brief = u"查看工单的权限"
schedule_work_command = Permission(ScheduleWorkCommand)
schedule_work_command.brief = u"调度工单的权限"

if __name__ == "__main__":
    from litefac.permissions.order import ViewOrder ,ScheduleOrder
    print ViewWorkCommand == ViewOrder
    print ScheduleOrder == ScheduleWorkCommand
