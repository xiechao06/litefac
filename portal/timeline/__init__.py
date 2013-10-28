#-*- coding:utf-8 -*-
from datetime import datetime, timedelta
from flask import Blueprint, request

time_line_page = Blueprint("timeline", __name__, static_folder="static",
                           template_folder="templates")

from litefac.portal.timeline import views
from litefac.basemain import data_browser, nav_bar

from nav_bar import NavBar


def get_sub_nav_bar():
    sub_nav_bar = NavBar()

    def _register_obj_cls(id_, title):
        kwargs = dict(request.args)
        if id_:
            kwargs["obj_class"] = id_
        else:
            try:
                del kwargs["obj_class"]
            except KeyError:
                pass
        sub_nav_bar.register(lambda: views.time_line_model_view.url_for_list(**kwargs), title,
                             enabler=lambda: views.obj_cls_fltr.real_value == str(id_) if id_ else not views.obj_cls_fltr.real_value)

    _register_obj_cls(None, u"所有")
    _register_obj_cls(views.ObjClsFilter.UNLOAD_SESSION, u"卸货会话")
    _register_obj_cls(views.ObjClsFilter.GOODS_RECEIPT, u"收货单")
    _register_obj_cls(views.ObjClsFilter.ORDER, u"订单")
    _register_obj_cls(views.ObjClsFilter.WORK_COMMAND, u"工单")
    return sub_nav_bar


def get_extra_params():
    return {
        "list_view": {
            "nav_bar": nav_bar,
            "sub_nav_bar": get_sub_nav_bar(),
            "titlename": u"时间线",
            "today": datetime.today().date(),
            "yesterday": datetime.today().date() - timedelta(days=1)
        },
    }


data_browser.register_model_view(views.time_line_model_view, time_line_page, extra_params=get_extra_params)
