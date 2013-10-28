# -*- coding: utf-8 -*-
from collections import namedtuple
from flask.ext.principal import Permission

DepartmentManagement = namedtuple("department", "method")
EditDepartment = DepartmentManagement("edit_department")

edit_department = Permission(EditDepartment)
edit_department = u"编辑车间的权限"




