# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
from flask import session, render_template, request
from flask.ext.login import current_user
from litefac.utilities import _
from path import path

# 导入基于角色的权限
from litefac.permissions.roles import (DepartmentLeaderPermission,
                                               QualityInspectorPermission,
                                               CargoClerkPermission,
                                               SchedulerPermission,
                                               AccountantPermission,
                                               AdminPermission)

# do a little magic
permissions = {}
from flask.ext.principal import Permission, RoleNeed

cur_dir = __path__[0]

for fname in path(cur_dir).files("[!_]*.py"):
    fname = fname.basename()[:-len(".py")]
    if fname == "roles":
        continue
    package = __import__(str("litefac.permissions."+fname), fromlist=[str(fname)])
    for k, v in package.__dict__.items():
        if isinstance(v, Permission):
            permissions[package.__name__.split(".")[-1] + "." + k] = {
                "needs": v.needs,
                "brief": v.brief
            }

def reset_permissions():
    global permissions
    permissions = {}

def install_permission(perm_name, needs, brief):
    permissions[perm_name] = {"needs": needs, "brief": brief}

if __name__ == "__main__":
    import pprint
    pprint.pprint(permissions)
    pprint.pprint(permissions["work_command.view_work_command"]["needs"].pop() == permissions["order.view_order"]["needs"].pop())
