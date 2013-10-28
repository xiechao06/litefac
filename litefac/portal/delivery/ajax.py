# -*- coding: UTF-8 -*-
import json
from flask import request, render_template, abort, flash
from socket import error
from wtforms import Form, IntegerField, BooleanField, TextField
from litefac.portal.delivery import delivery_page
from litefac.utilities.decorators import ajax_call
from litefac.utilities import _


@delivery_page.route("/ajax/consignment-list", methods=["GET"])
@ajax_call
def consignment_list():
    session_id = request.args.get("delivery_session_id", type=int)
    if session_id is not None:
        import litefac.apis as apis

        consignments, totalcnt = apis.delivery.get_consignment_list(session_id)
        if not consignments:
            return _(u"当前没有任何发货单"), 404
        return json.dumps(
            [dict(id=c.id, customer=c.customer.name,
                  consignment_id=c.consignment_id) for c in consignments])
    else:
        return _(u"未选择发货会话"), 403


@delivery_page.route("/ajax/consignment", methods=["POST"])
@ajax_call
def ajax_consignment():
    class _ConsignmentForm(Form):
        id = IntegerField("id")

    form = _ConsignmentForm(request.form)
    consignment_id = form.id.data
    if consignment_id:
        import litefac.apis as apis
        cons = apis.delivery.get_consignment(consignment_id)
        if not cons:
            return _(u"不存在该发货单%d" % consignment_id), 404
        elif not cons.MSSQL_ID:
            try:
                MSSQL_ID = json.loads(apis.broker.export_consignment(cons))
            except (ValueError, error):
                return _(u"插入MS SQL失败，请手工插入"), 403
            try:
                apis.delivery.ConsignmentWrapper.update(consignment_id, MSSQL_ID=MSSQL_ID["id"])
            except ValueError, e:
                return e.message, 403
            except:
                return _(u"更新失败"), 403
            return _(u"更新成功")
    else:
        return _(u"数据错误"), 404


@delivery_page.route("/ajax/customer-list")
@ajax_call
def customer_list():
    """
    return the customers, params include:
    * delivery_session_id
    """
    delivery_session_id = request.args.get("delivery_session_id", type=int)
    customers = []
    if delivery_session_id is not None:
        import litefac.apis as apis

        delivery_session = apis.delivery.get_delivery_session(
            delivery_session_id)
        if not delivery_session.finish_time:
            return _(u"发货会话尚未结束"), 403
        if any(task.weight == 0 for task in delivery_session.delivery_task_list):
            return _(u"请先对所有的发货任务进行称重"), 403

        acked_customer_id_list = set([gr.customer_id for gr in
                                      delivery_session.consignment_list])
        customers = [c for c in delivery_session.customer_list if
                     c.id not in acked_customer_id_list]
        if not customers:
            return _(u"已经对所有的客户生成了发货单"), 403

    return json.dumps([{"id": c.id, "name": c.name} for c in customers])

@delivery_page.route("/ajax/delivery-task/<int:id_>", methods=["POST"])
@ajax_call
def delivery_task(id_):
    from litefac import apis
    task = apis.delivery.get_delivery_task(id_)
    if not task:
        abort(404)
    if task.weight:
        return _(u"已称重的发货任务不能删除"), 403
    try:
        task.delete()
        flash(u"删除成功")
        return "success"
    except Exception, e:
        return unicode(e), 403
