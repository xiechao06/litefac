#-*- coding:utf-8 -*-
from flask import redirect, url_for, request
from flask.ext.databrowser.action import BaseAction, DirectAction, DeleteAction

from litefac.utilities.decorators import committed
from litefac import constants


class CloseAction(BaseAction):
    def test_enabled(self, model):
        if model.status in [constants.delivery.STATUS_CLOSED, constants.delivery.STATUS_DISMISSED]:
            return -2
        if not all(task.weight for task in model.delivery_task_list):
            return -3
        return 0

    def op(self, obj):
        from litefac.portal.delivery.fsm import fsm
        from flask.ext.login import current_user

        fsm.reset_obj(obj)
        fsm.next(constants.delivery.ACT_CLOSE, current_user)

    def get_forbidden_msg_formats(self):
        return {-2: u"发货会话%s已经被关闭",
                -3: u"发货会话%s有发货任务没有称重，请确保所有的发货任务都已经称重！"}


class OpenAction(BaseAction):
    def test_enabled(self, model):
        if model.status != constants.delivery.STATUS_CLOSED:
            return -2
        if any(cn.MSSQL_ID for cn in model.consignment_list):
            return -3
        return 0

    def op(self, obj):
        from litefac.portal.delivery.fsm import fsm
        from flask.ext.login import current_user

        fsm.reset_obj(obj)
        fsm.next(constants.delivery.ACT_OPEN, current_user)

    def get_forbidden_msg_formats(self):
        return {-2: u"发货会话%s处在打开状态, 只有已经关闭的会话才能被打开",
                -3: u"发货会话%s存在已导入旧系统的发货单，无法重新打开"}


class CreateConsignmentAction(DirectAction):
    """
    生成发货单是很特殊的action。需要传入额外的参数。
    """
    def test_enabled(self, model):
        if model.consignment_list:
            if all(not cn.stale for cn in model.consignment_list) and len(
                    model.consignment_list) == len(model.customer_list):
                return -2
            if any(cn.MSSQL_ID for cn in model.consignment_list):
                return -3
            if any(cn.pay_in_cash and cn.is_paid for cn in model.consignment_list):
                return -5
        elif not model.delivery_task_list:
            return -4
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"发货会话%s已生成发货单",
                -3: u"发货会话%s存在已导入旧系统的发货单，无法重新生成",
                -4: u"发货会话%s没有发货任务，请先生成发货任务",
                -5: u"发货会话%s的发货单已支付"}


class BatchPrintConsignment(DirectAction):
    def op_upon_list(self, objs, model_view):
        for obj in objs:
            model_view.do_update_log(obj, self.name)
        return redirect(url_for("consignment.batch_print_consignment", delivery_session_id=[obj.id for obj in objs],
                                url=request.url))

    def test_enabled(self, model):
        if not model.consignment_list:
            return -2
        if any(cn.pay_in_cash and not cn.is_paid for cn in model.consignment_list):
            return -3
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"发货会话%s未生成发货单", -3: u"发货会话%s有未支付的发货单"}


class PayAction(BaseAction):
    def test_enabled(self, model):
        if model.stale:
            return -2
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"发货单%s已过时，请联系收发员重新生成"}

    @committed
    def op(self, obj):
        obj.is_paid = True
        obj.remove_todo()


class PreviewConsignment(DirectAction):
    def op_upon_list(self, objs, model_view):
        return redirect(url_for("delivery.consignment_preview", id_=objs[0].id, url=request.url))


class DeleteDeliverySession(DeleteAction):

    def test_enabled(self, model):
        if model.consignment_list:
            return -2
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"发货会话%s已经生成了发货单，请先删除对应发货单以后再删除此发货会话!"}

    def op(self, obj):
        from litefac.apis.todo import remove_todo, WEIGH_DELIVERY_TASK
        for task in obj.delivery_task_list:
            remove_todo(WEIGH_DELIVERY_TASK, task.id)
        super(DeleteDeliverySession, self).op(obj)

class DeleteConsignment(DeleteAction):

    def test_enabled(self, model):
        if model.MSSQL_ID:
            return -2
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"已导入到MSSQL的发货单不能删除"}