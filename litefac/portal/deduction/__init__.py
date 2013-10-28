# -*- coding: UTF-8 -*-
import os

from flask import Blueprint, redirect, url_for
from litefac.basemain import data_browser
from litefac.permissions.deduction import addDeduction, editDeduction, deleteDeduction
from datetime import datetime

deduction_page = Blueprint("deduction", __name__, static_folder="static",
    template_folder="templates")

from litefac.database import db
from litefac import models

from litefac.basemain import nav_bar
from flask.ext.databrowser import ModelView
from litefac.basemain import app

@deduction_page.route('/')
def index():
    return redirect(url_for("deduction.deduction_list"))

class DeductionModelView(ModelView):
    __create_columns__ = ["id", "weight", "work_command", "team", "remark"]

    __list_columns__ = ["id", "weight", "work_command", "team", "actor",
                        "create_time", "remark"]

    __column_labels__ = {
        "weight": u"重量",
        "work_command": u"工单号",
        "team": u"班组",
        "actor": u"质检员",
        "create_time": u"创建于",
        "remark": u"备注",
    }

    __list_formatters__ = {
        "team": lambda model, v: v.name,
        "weight": lambda model, v: str(v) if v else "" + u'(公斤)',
        "actor": lambda model, v: v.username,
        "create_time": lambda model, v: v.strftime("%Y-%m-%d %H") + u"点",
        "remark": lambda model, v: v or "-",
        "work_command": lambda model,v:v.id if v else "-"
    }
    form_formatters = {"work_command": lambda work_command: work_command.id,
                       "team": lambda team:team.name,
                       "actor": lambda actor:actor.username
                       }

    __sortable_columns__ = ["id", "weight", "work_command", "team", "actor", "create_time"]

    from flask.ext.databrowser import filters
    from datetime import datetime, timedelta
    today = datetime.today()
    yesterday = today.date()
    week_ago = (today - timedelta(days=7)).date()
    _30days_ago = (today - timedelta(days=30)).date()
    __column_filters__ = [filters.EqualTo("team", name=u"是", opt_formatter=lambda opt: opt.name),
                         filters.BiggerThan("create_time", name=u"在",
                                            options=[(yesterday, u'一天内'),
                                                    (week_ago, u'一周内'),
                                                    (_30days_ago, u'30天内')]),
                         filters.EqualTo("id", name=u"是"),
                         filters.LessThan("weight", name=u"小于"),
                         filters.EqualTo("work_command", name=u"等于", opt_formatter=lambda opt:opt.id)]

    def can_create(self):
        return addDeduction.can()

    def can_edit(self):
        return editDeduction.can()

    def can_delete(self):
        return deleteDeduction.can()

    def on_model_change(self, form, model):
        from flask.ext.login import current_user
        model.actor = current_user
        if not model.create_time:
            model.create_time = datetime.now()

extra_params = {
    "list_view": {
        'nav_bar': nav_bar
    }
}
data_browser.register_model_view(DeductionModelView(models.Deduction), deduction_page,
                                     extra_params)
