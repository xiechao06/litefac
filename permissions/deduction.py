# -*- coding: UTF-8 -*-
from collections import namedtuple
from flask.ext.principal import Permission

DeductionManagement = namedtuple("deduction", ["method"])

ViewDeduction = DeductionManagement("view_deduction")

AddDeduction = DeductionManagement("add_deduction")

EditDeduction = DeductionManagement("edit_deduction")

DeleteDeduction = DeductionManagement("delete_deduction")

view_deduction = Permission(ViewDeduction)
view_deduction.brief = u"查看扣重的权限"

addDeduction = Permission(AddDeduction)
addDeduction.brief = u"增加扣重的权限"

editDeduction = Permission(EditDeduction)
editDeduction.brief = u'修改扣重的权限'

deleteDeduction = Permission(DeleteDeduction)
deleteDeduction.brief = u'删除扣重的权限'
