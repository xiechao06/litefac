# -*- coding: UTF-8 -*-
import json
from flask import request, flash
from sqlalchemy.exc import SQLAlchemyError
from wtforms import Form, TextField, IntegerField
from litefac import constants
from litefac.portal.cargo import cargo_page
from litefac.utilities import get_or_404, do_commit
from litefac.utilities.decorators import ajax_call
from litefac.models import UnloadSession, GoodsReceipt, UnloadTask
from flask.ext.babel import _

@cargo_page.route("/ajax/receipts-list", methods=["GET"])
@ajax_call
def receipts_list():
    session_id = request.args.get("unload_session_id", type=int)
    if session_id is not None:
        import litefac.apis as apis

        receipts = apis.cargo.get_goods_receipts_list(session_id)
        if not receipts:
            return _(u"当前没有任何收货单"), 404
        return json.dumps([dict(id=r.id, receipt_id=str(r.receipt_id),
                                customer=r.customer.name)
                           for r in receipts])
    else:
        return u"未选择卸货会话", 403


@cargo_page.route("/ajax/goods-receipt", methods=["POST"])
@ajax_call
def ajax_receipt():
    class _POST_Form(Form):
        id = TextField("id")
        task_id = TextField("task_id")
        product_id = TextField("product_id")
        weight = IntegerField("weight")


    form = _POST_Form(request.form)
    receipt_id = form.id.data

    if receipt_id:
        try:
            import litefac.apis as apis

            apis.cargo.get_goods_receipt(receipt_id).update(
                printed=True)
            return _(u"更新成功")
        except SQLAlchemyError:
            return _(u"更新失败"), 403
        except AttributeError:
            return _(u"无此收货单"), 404
    else:
        task_id = form.task_id.data
        product_id = form.product_id.data
        weight = form.weight.data or '' #integer field默认值为None。所以需要将None设置为''
        import litefac.apis as apis

        ut = apis.cargo.get_unload_task(task_id)
        if not ut or not (product_id or weight):
            return _(u"数据错误"), 404
        try:
            if ut.sub_order:
                ut.sub_order.update(product_id=product_id, weight=weight)
            ut.update(product_id=product_id, weight=weight)
            return _(u"更新成功")
        except ValueError, e:
            return unicode(e), 403
        except SQLAlchemyError:
            return _(u"更新失败"), 403

def _log2dict(log):
    return {
        "obj_cls": u"卸货会话" if log.obj_cls == "UnloadSession" else u"卸货任务",
        "action": log.action,
        "create_time": log.create_time.strftime("%y-%m-%d %H:%M:%S"),
        "actor": log.actor.username,
        "obj": unicode(log.obj),
        "message": log.message
    }

@cargo_page.route("/ajax/gr-log-list", methods=["GET"])
def gr_log_list():
    gr_id = int(request.args["gr_id"])
    gr = get_or_404(GoodsReceipt, gr_id)
    log_list = gr.log_list
    return json.dumps({
        "count": len(log_list),
        "data": [_log2dict(log) for log in log_list if log.obj_cls in {"GoodsReceipt", "GoodsReceiptEntry"}],
    })

@cargo_page.route("/ajax/us-log-list", methods=["GET"])
def us_log_list():
    us_id = int(request.args["us_id"])
    us = get_or_404(UnloadSession, us_id)
    log_list = us.log_list
    return json.dumps({
        "count": len(log_list),
        "data": [_log2dict(log) for log in log_list if log.obj_cls in {"UnloadSession", "UnloadTask"}],
    })


@cargo_page.route("/ajax/unload-task/<int:id_>", methods=["POST"])
@ajax_call
def unload_task(id_):
    if request.form["action"] == "delete":
        ut = get_or_404(UnloadTask, id_)
        if ut.weight != 0:
            return u"已经称重的卸货任务不能删除", 403
        else:
            if ut.delete():
                flash(u"删除卸货任务%d成功" % ut.id)
                return "success"
        return "error", 403
