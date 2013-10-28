# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
from flask import Blueprint, render_template, request
from flask.ext.login import login_required
from litefac.utilities.decorators import nav_bar_set

store_bill_page = Blueprint("store_bill", __name__, static_folder="static",
                            template_folder="templates")

from . import ajax
from .views import store_bill_view

from litefac.basemain import data_browser,nav_bar

data_browser.register_model_view(store_bill_view, store_bill_page,
                                 extra_params={"list_view": {"nav_bar": nav_bar, "titlename": u"仓单列表"},
                                               "form_view": {"nav_bar": nav_bar, "titlename": u"编辑仓单"}})

@store_bill_page.route("/to_delivery_list", methods=["GET", "POST"])
def to_delivery_list():
    if request.method == "GET":
        from litefac.apis.delivery import get_store_bill_customer_list
        list_ = get_store_bill_customer_list()
        return render_template("delivery/store-bill-list.html", customer_list=list_, titlename=u"仓单列表",
                               nav_bar=nav_bar)
    else:
        pass

@store_bill_page.before_request
@login_required
def _():
    pass
