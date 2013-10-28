# -*- coding: UTF-8 -*-

from flask import Blueprint
from litefac.permissions import CargoClerkPermission

cargo_page = Blueprint("cargo", __name__, static_folder="static", template_folder="templates")

gr_page = Blueprint("goods_receipt", __name__, static_folder="static", template_folder="templates")


from litefac.portal.cargo.views import (unload_session_model_view,
                                         plate_model_view,
                                         goods_receipt_entry_view,
                                         goods_receipt_model_view,
                                         unload_task_model_view)

from litefac.basemain import data_browser, nav_bar

def _do_register(model_view, bp):
    extra_params = {
        "list_view": {
            "nav_bar": nav_bar,
            "titlename": model_view.model_name + u"列表",
        },
        "create_view": {
            "nav_bar": nav_bar,
            "titlename": u"创建" + model_view.model_name,
        },
        "form_view": {
            "nav_bar": nav_bar,
            "titlename": u"编辑" + model_view.model_name,
        }

    }
    data_browser.register_model_view(model_view, bp, extra_params)

for model_view in [unload_session_model_view, goods_receipt_entry_view,
                   plate_model_view, 
                   unload_task_model_view]:
    _do_register(model_view, cargo_page)

for model_view in [goods_receipt_model_view]:
    _do_register(model_view, gr_page)

from . import views, ajax
