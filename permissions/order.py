# -*- coding: utf-8 -*-
"""
针对订单对象的权限，将用户管理相关的权限
"""
from collections import namedtuple
from flask.ext.principal import Permission

SubOrderManagement = namedtuple("sub_order", ["method"])

EditSubOrderWeight = SubOrderManagement("edit_sub_order_weight")

edit_sub_order_weight = Permission(EditSubOrderWeight) 
edit_sub_order_weight.brief = u"修改子订单重量的权限"

OrderManagement = namedtuple("order", ["method"])
ViewOrder = OrderManagement("view_order")
ScheduleOrder = OrderManagement("schedule_order")

view_order = Permission(ViewOrder)
view_order.brief = u"查看订单的权限"
schedule_order = Permission(ScheduleOrder)
schedule_order.brief = u"调度订单的权限"
