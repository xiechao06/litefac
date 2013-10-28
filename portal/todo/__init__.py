#-*- coding:utf-8 -*-
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, flash
from litefac.basemain import data_browser, nav_bar

from .views import to_do_view

to_do_page = Blueprint("todo", __name__, static_folder="static",
                       template_folder="templates")

data_browser.register_model_view(to_do_view, to_do_page,
                                 extra_params={
                                     "list_view": {
                                         "nav_bar": nav_bar,
                                         "titlename": u"待办事项",
                                         "today": datetime.today().date(),
                                         "yesterday": datetime.today().date() - timedelta(days=1)
                                     }
                                 })


@to_do_page.route("/delete/<int:id_>", methods=["POST"])
def delete(id_):
    from litefac.apis.todo import delete_todo

    try:
        delete_todo(id_)
        flash(u"删除待办事项%d成功" % id_)
    except:
        flash(u"删除待办事项%d失败" % id_, "error")
    return redirect(url_for("todo.todo_list", _method="GET"))