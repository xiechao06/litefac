#-*- coding:utf-8 -*-
from flask import Blueprint, render_template
from flask.ext.principal import PermissionDenied
from litefac.utilities.decorators import templated, nav_bar_set

dashboard = Blueprint(name="dashboard", import_name=__name__, static_folder="static", template_folder="templates")


class Widget(object):
    def __init__(self, name, description, template_file=None):
        self.name = name
        self.description = description
        self.template_file = template_file or "dashboard/widget.html"

    def template(self):
        return render_template(self.template_file, widget=self)

    @property
    def data(self):
        return self.query()

    def query(self):
        return NotImplemented

    def try_view(self):
        return True


DASHBOARD_WIDGETS = []
from . import widgets


def _get_widgets():
    result = []
    for i in DASHBOARD_WIDGETS:
        try:
            i.try_view()
            result.append(i)
        except PermissionDenied:
            pass
    return result


@dashboard.route("/")
@templated("dashboard/index.html")
@nav_bar_set
def index():
    return {"titlename": u"仪表盘", "widgets": _get_widgets()}


