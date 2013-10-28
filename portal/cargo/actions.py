# -*- coding: utf-8 -*-
from flask import url_for, redirect, request
from flask.ext.databrowser.action import DeleteAction, BaseAction, DirectAction
from flask.ext.login import current_user
from litefac import constants
from litefac.constants import cargo as cargo_const


class DeleteUnloadSessionAction(DeleteAction):
    def test_enabled(self, model):
        if model.goods_receipt_list:
            return -2
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"收货会话%s已经生成了收货单，请先删除对应收货单以后再删除此收货会话!"}

    def op(self, obj):
        from litefac.apis.todo import remove_todo, WEIGH_UNLOAD_TASK
        for task in obj.task_list:
            remove_todo(WEIGH_UNLOAD_TASK, task.id)
        super(DeleteUnloadSessionAction, self).op(obj)

class CloseAction(BaseAction):
    def test_enabled(self, model):
        if model.status in [cargo_const.STATUS_CLOSED, cargo_const.STATUS_DISMISSED]:
            return -2
        if not all(task.weight for task in model.task_list):
            return -3
        return 0

    def op(self, obj):
        from litefac.portal.cargo.fsm import fsm
        from flask.ext.login import current_user

        fsm.reset_obj(obj)
        fsm.next(cargo_const.ACT_CLOSE, current_user)

    def get_forbidden_msg_formats(self):
        return {-2: u"收货会话%s已经被关闭",
                -3: u"收货会话%s有卸货任务没有称重，请确保所有的卸货任务都已经称重！"}


class OpenAction(BaseAction):
    def test_enabled(self, model):
        if model.status != cargo_const.STATUS_CLOSED:
            return -2
        return 0

    def op(self, obj):
        from litefac.portal.cargo.fsm import fsm
        from flask.ext.login import current_user

        fsm.reset_obj(obj)
        fsm.next(cargo_const.ACT_OPEN, current_user)

    def get_forbidden_msg_formats(self):
        return {-2: u"收货会话%s处在打开状态, 只有已经关闭的会话才能被打开"}

class CreateReceiptAction(BaseAction):
    def test_enabled(self, model):
        if model.goods_receipt_list and all(not gr.stale for gr in model.goods_receipt_list) and len(
                model.goods_receipt_list) == len(model.customer_list):
            return -2
        elif not model.task_list:
            return -3
        return 0

    def op(self, obj):
        obj.clean_goods_receipts()

    def get_forbidden_msg_formats(self):
        return {-2: u"卸货会话%s已生成收货单", -3: u"卸货会话%s没有卸货任务，请先生成卸货任务"}

class PrintGoodsReceipt(DirectAction):
    def op_upon_list(self, objs, model_view):
        model_view.do_update_log(objs[0], self.name)
        return redirect(url_for("cargo.goods_receipt_preview", id_=objs[0].id, url=request.url))

class BatchPrintGoodsReceipt(DirectAction):
    def op_upon_list(self, objs, model_view):
        for obj in objs:
            model_view.do_update_log(obj, self.name)
        return redirect(
            url_for("goods_receipt.goods_receipts_batch_print", id_=",".join([str(obj.id) for obj in objs]),
                    url=request.url))


class CreateOrderAction(BaseAction):
    def test_enabled(self, model):
        if model.order:
            return -2
        return 0

    def op(self, obj):
        from litefac.apis.order import new_order

        new_order(obj.id, constants.STANDARD_ORDER_TYPE, current_user.id)

    def get_forbidden_msg_formats(self):
        return {-2: u"已生成订单"}


class CreateExtraOrderAction(BaseAction):
    def test_enabled(self, model):
        if model.order:
            return -2
        return 0

    def op(self, obj):
        from litefac.apis.order import new_order

        new_order(obj.id, constants.EXTRA_ORDER_TYPE, current_user.id)

    def get_forbidden_msg_formats(self):
        return {-2: u"已生成订单"}


class ViewOrderAction(DirectAction):
    def test_enabled(self, model):
        if model.order:
            return 0
        return -2

    def get_forbidden_msg_formats(self):
        return {-2: u"未生成订单"}

    def op_upon_list(self, objs, model_view):
        return redirect(url_for("order.order", id_=objs[0].order.id, url=request.url))


class DeleteGoodsReceiptAction(DeleteAction):
    def test_enabled(self, model):
        if model.order:
            return -2
        if model.printed:
            return -3
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"已生成订单的收货单不能删除", -3: u"已经打印的收货单不能删除"}
