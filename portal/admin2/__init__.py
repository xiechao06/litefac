# -*- coding: UTF-8 -*-
import socket
import errno

from flask import Blueprint, request, url_for, render_template, redirect
from litefac.basemain import data_browser, nav_bar

admin2_page = Blueprint("admin2", __name__, static_folder="static", 
                       template_folder="templates")

from litefac.portal.admin2.views import (user_model_view, group_model_view,
                                          department_model_view,
                                          team_model_view, harbor_model_view,
                                          procedure_model_view, config_model_view, 
                                          customer_model_view, product_model_view)
from nav_bar import NavBar
sub_nav_bar = NavBar()
sub_nav_bar.register(lambda: user_model_view.url_for_list(), u"用户管理",
    enabler=lambda: user_model_view.within_domain(request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: group_model_view.url_for_list(), u"用户组管理", 
    enabler=lambda: group_model_view.within_domain(request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: customer_model_view.url_for_list(), u"客户管理", 
    enabler=lambda: customer_model_view.within_domain(request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: department_model_view.url_for_list(), u"车间管理", 
    enabler=lambda: department_model_view.within_domain(request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: team_model_view.url_for_list(), u"班组管理", 
    enabler=lambda: team_model_view.within_domain(request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: harbor_model_view.url_for_list(), u"装卸点管理", 
    enabler=lambda: harbor_model_view.within_domain(request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: procedure_model_view.url_for_list(), u"工序管理", 
    enabler=lambda: procedure_model_view.within_domain(request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: product_model_view.url_for_list(), u"产品管理",
                     enabler=lambda: product_model_view.within_domain(
                         request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: config_model_view.url_for_list(), u"配置项管理",
                     enabler=lambda: config_model_view.within_domain(
                         request.url, "admin2"), group=u"对象管理")
sub_nav_bar.register(lambda: url_for("admin2.broker_index"), u"数据导入", 
    enabler=lambda: "admin2/broker" in request.url, group=u"其它管理")

@admin2_page.route("/")
def index():
    return redirect(url_for("admin2.user_list"))

def _do_register(model_name, model_view):
    extra_params = {
        "list_view": {
            "nav_bar": nav_bar,
            "sub_nav_bar": sub_nav_bar,
            "titlename": model_name + u"管理",
        },
        "create_view": {
            "nav_bar": nav_bar,
            "sub_nav_bar": sub_nav_bar,
            "titlename": u"创建" + model_name,
        },
        "form_view": {
            "nav_bar": nav_bar,
            "sub_nav_bar": sub_nav_bar,
            "titlename": u"编辑" + model_name,
        }
    }
    data_browser.register_model_view(model_view, admin2_page, extra_params=extra_params)


for mn, mv in [(u"用户", user_model_view), (u"用户组", group_model_view),
               (u"车间", department_model_view), (u"班组", team_model_view),
               (u"装卸点", harbor_model_view), (u"工序", procedure_model_view),
               (u"配置项", config_model_view), (u"客户", customer_model_view),
               (u"产品", product_model_view)]:
    _do_register(mn, mv)

@admin2_page.errorhandler(socket.error)
def connection_refused(e):
    if e.errno == errno.ECONNREFUSED:
        return render_template("error.html", msg=u"无法连接", titlename=u"无法连接")
    else:
        return render_template("error.html", msg=e, titlename=u"连接失败")
