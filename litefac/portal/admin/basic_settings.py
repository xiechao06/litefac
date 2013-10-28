# -*- coding: utf-8 -*-
from flask.ext.admin import BaseView, Admin, expose
from litefac.permissions import AdminPermission

class BasicSettings(BaseView):
    def is_accessible(self):
        return AdminPermission.can()

    @expose("/")
    def index(self):
        return self.render("admin/basic_settings/index.html")


