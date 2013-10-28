# -*- coding: utf-8 -*-
"""
针对用户对象的权限，将用户管理相关的权限
"""
from collections import namedtuple
from flask.ext.principal import Permission

AccountManagement = namedtuple("user", ["method"])

# 针对班组长的管理权限
ViewDepartmentLeader = AccountManagement("view_account")
EditDepartmentLeader = AccountManagement("edit_account")
NewDepartmentLeader = AccountManagement("new_account")
DelDepartmentLeader = AccountManagement("delete_account")

view_dl = Permission(ViewDepartmentLeader)
view_dl.brief = u"查看车间主任账户信息的权限"

edit_dl = Permission(EditDepartmentLeader)
edit_dl.brief = u"修改车间主任账户信息的权限"

new_dl = Permission(NewDepartmentLeader)
new_dl.brief = u"创建车间主任账户的权限"

del_dl = Permission(DelDepartmentLeader)
del_dl.brief = u"删除车间主任账户的权限"

admin_dl = Permission(ViewDepartmentLeader, EditDepartmentLeader, 
                     NewDepartmentLeader, DelDepartmentLeader)
admin_dl.brief = u"对车间主任帐号有增删改查权限"

if __name__ == "__main__":
    print view_dl.brief
