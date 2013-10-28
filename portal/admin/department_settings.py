# -*- coding: utf-8 -*-
from flask.ext.admin.contrib.sqlamodel import ModelView

import flask.ext.admin
from litefac.permissions import AdminPermission

class DepartmentModelView(ModelView):
    column_list = ("name", "leader_list")
    column_labels = {"name": u"名称", "leader_list": u"车间主任"}
    list_formatters = {"leader_list": lambda context, model, name: ", ".join([u.username for u in model.leader_list])}

    def is_accessible(self):
        return AdminPermission.can()
