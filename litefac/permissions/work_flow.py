# -*- coding: UTF-8 -*-

from collections import namedtuple
from flask.ext.principal import Permission

WorkFlowManagement = namedtuple("user", ["method"])

HandleNodeNeed = WorkFlowManagement('handle_node')

handle_node = Permission(HandleNodeNeed)
handle_node.brief = u'处理工作流的权限'

