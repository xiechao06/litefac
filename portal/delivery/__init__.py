# -*- coding: UTF-8 -*-

from flask import Blueprint, redirect, request, abort
from flask.ext.login import login_required
from litefac.utilities.decorators import templated

delivery_page = Blueprint("delivery", __name__, static_folder="static", template_folder="templates")

consignment_page = Blueprint("consignment", __name__, static_folder="static", template_folder="templates")

from litefac.portal.delivery import views, ajax

from litefac.basemain import data_browser, nav_bar

extra_params = {
    "list_view": {
        "nav_bar": nav_bar,
        "titlename": u"发货单列表",
    },
    "form_view": {
        "nav_bar": nav_bar,
        "titlename": u"编辑发货单",
    }
}
data_browser.register_model_view(views.consigment_model_view, consignment_page, extra_params)

extra_params = {
    "form_view": {
        "nav_bar": nav_bar,
        "titlename": u"编辑发货单项",
    }
}
data_browser.register_model_view(views.consigment_product_model_view, consignment_page, extra_params)

from litefac.apis import delivery
get_customer_list = delivery.get_store_bill_customer_list

data_browser.register_model_view(views.delivery_session_view, delivery_page,
                                 extra_params={"list_view": {"nav_bar": nav_bar, "titlename": u"发货会话列表"},
                                               "create_view": {"nav_bar": nav_bar, "titlename": u"新建发货会话", "get_customer_list": get_customer_list},
                                               "form_view": {"nav_bar": nav_bar, "titlename": u"编辑发货会话"}})

data_browser.register_model_view(views.delivery_task_view, delivery_page,
                                 extra_params={"form_view": {"nav_bar": nav_bar, "titlename": u"编辑任务会话"}})

@consignment_page.route("/")
def index():
    return redirect(views.consigment_model_view.url_for_list())

@consignment_page.before_request
@login_required
def _default():
    pass

@consignment_page.route("/batch-print/")
@templated("delivery/batch-print-consignment.html")
def batch_print_consignment():
    from litefac import apis
    from flask import json
    from socket import error

    delivery_session_id_list = request.args.getlist("delivery_session_id", type=int)
    if not delivery_session_id_list:
        abort(404)
    error_message = ""
    consignment_list = []

    per_page = apis.config.get("print_count_per_page", 5, type=int)
    for delivery_session in [apis.delivery.get_delivery_session(id_) for id_ in delivery_session_id_list]:

        for cn in delivery_session.consignment_list:
            if not cn.MSSQL_ID:
                try:
                    MSSQL_ID = json.loads(apis.broker.export_consignment(cn))
                except error:
                    error_message += u"发货单%s，" % cn.id
            consignment_list.append(cn)
    if error_message:
        error_message += u"插入MSSQL失败，请手工插入"
    return {"consignment_list": consignment_list, "error_message": error_message,
            "per_page": per_page, "nav_bar": nav_bar, "url": request.args.get("url"), "titlename": u"批量打印"}

@delivery_page.before_request
@login_required
def _default():
    pass

