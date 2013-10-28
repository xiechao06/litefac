# -*- coding: UTF-8 -*-
import json
from flask import request, render_template, url_for
from litefac.utilities import _
from litefac.portal.order import order_page
from litefac.utilities import decorators
from litefac.utilities.decorators import ajax_call


@order_page.route("/ajax/customer-list")
@ajax_call
def customer_list():
    """
    return the customers, params include:
    * unload_session_id
    """
    unload_session_id = request.args.get("unload_session_id", None)
    customers = []
    if unload_session_id:
        unload_session_id = int(unload_session_id)
        from litefac import apis

        unload_session = apis.cargo.get_unload_session(unload_session_id)
        if not unload_session.finish_time:
            return _(u"卸货会话尚未结束"), 403
        if any(task.weight == 0 for task in unload_session.task_list):
            return _(u"请先对所有的卸货任务进行称重"), 403
        acked_customer_id_list = set([gr.customer_id for gr in
                                      unload_session.goods_receipt_list])
        customers = [c for c in unload_session.customer_list if
                     c.id not in acked_customer_id_list]
    if not customers:
        return _(u"已经对所有的用户生成了收货单"), 403
    return json.dumps([{"id": c.id, "name": c.name} for c in customers])


@order_page.route("/ajax/order-modify", methods=["POST"])
@ajax_call
def order_modify():
    from litefac import apis

    order = apis.order.get_order(request.form["order_id"])
    if not order:
        return _(u"不存在订单ID为%s的订单" % request.form["order_id"]), 403
    if any(
            sub_order.work_command_list for sub_order in order.sub_order_list):
        return _(u"该订单已排产，请勿修改"), 500
    try:
        order.update(customer_order_number=request.form["customer_order_number"])
        return _(u"修改成功")
    except ValueError:
        return _(u"修改失败"), 403


@order_page.route("/ajax/sub-order", methods=["GET"])
@ajax_call
def ajax_sub_order():
    sub_order_id = request.args.get('id', type=int)
    if not sub_order_id:
        return _(u"不存在该订单"), 404
    from litefac import apis

    inst = apis.order.get_sub_order(sub_order_id)
    if not inst:
        return "no sub order with id " + str(sub_order_id), 404
    from litefac.basemain import nav_bar
    from litefac.constants import DEFAULT_PRODUCT_NAME

    param_dict = {'titlename': u'子订单详情', 'sub_order': inst, 'nav_bar': nav_bar,
                  'DEFAULT_PRODUCT_NAME': DEFAULT_PRODUCT_NAME}
    param_dict.update(product_types=apis.product.get_product_types())
    param_dict.update(products=json.dumps(apis.product.get_products()))
    param_dict.update(harbor_list=apis.harbor.get_harbor_list())
    purl = request.args.get("purl")
    if purl is None or purl == "None":
        purl = url_for("order.order_list")
    param_dict.update(purl=purl)
    return render_template("order/sub-order.html", **param_dict)


@order_page.route("/ajax/team-work-reports", methods=["GET"])
@ajax_call
def team_work_reports():
    ret = {}
    from litefac.apis.order import get_order

    order = get_order(request.args.get("order_id", type=int))
    for wc in order.done_work_command_list:
        try:
            ret[wc.team.name] += wc.processed_weight
        except KeyError:
            ret[wc.team.name] = wc.processed_weight
    return json.dumps(ret.items())


@order_page.route("/ajax/team-manufacturing-reports", methods=["GET"])
@ajax_call
def team_manufacturing_reports():
    from litefac.apis.order import get_order

    order = get_order(request.args.get("order_id", type=int))
    d = {}
    for so in order.sub_order_list:
        for wc in so.manufacturing_work_command_list:
            team_name = wc.department.name + u"车间:" + (wc.team.name if wc.team else u"尚未分配") + u"班组"
            try:
                d[team_name] += wc.org_weight
            except KeyError:
                d[team_name] = wc.org_weight
    return json.dumps(sorted([dict(team=k, weight=v) for k, v in d.items()], key=lambda v: v["team"]))


@order_page.route("/ajax/store-bill-list", methods=["GET"])
@ajax_call
def store_bill_list():
    from litefac.apis.order import get_order

    order = get_order(request.args.get("order_id", type=int))
    ret = []
    for so in order.sub_order_list:
        for sb in so.store_bill_list:
            ret.append(dict(id=sb.id, product=so.product.name, spec=so.spec, type=so.type, weight=sb.weight))
    return json.dumps(ret)