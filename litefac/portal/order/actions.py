# -*- coding: utf-8 -*-
from datetime import datetime
from flask.ext.databrowser.action import BaseAction, DirectAction
from flask import redirect, request, url_for


class DispatchAction(BaseAction):
    
    def op(self, model):
        model.update(dispatched=True, dispatched_time=datetime.now())
        model.add_todo()


    def test_enabled(self, model):
        if model.dispatched:
            return -2
        elif not model.refined:
            return -3
        return 0 
    
    def get_forbidden_msg_formats(self):
        return {
            -2: u"订单[%s]已经下发,不能重复下发",
            -3: u"订单[%s]没有完善，请先完善"
        }
    
    def try_(self, preprocessed_objs):
        from litefac.permissions import CargoClerkPermission,AdminPermission
        from flask.ext.principal import Permission
        Permission.union(CargoClerkPermission, AdminPermission).test()
    
class AccountAction(BaseAction):
    def op(self, order):
        from litefac import apis
        for sub_order in order.sub_order_list:
            for store_bill in sub_order.store_bill_list:
                fake_delivery_task = apis.delivery.fake_delivery_task()
                if not store_bill.delivery_task:
                    apis.delivery.update_store_bill(store_bill.id,
                                                    delivery_session_id=fake_delivery_task.delivery_session.id,
                                                    delivery_task_id=fake_delivery_task.id)
            sub_order.end()
        order.update(
            finish_time=datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"))


    def try_(self, preprocessed_objs):
        from litefac.permissions import CargoClerkPermission,AdminPermission
        from flask.ext.principal import Permission
        Permission.union(CargoClerkPermission, AdminPermission).test()

    def test_enabled(self, model):
        if not model.can_account:
            return -1

    def get_forbidden_msg_formats(self):
        return {
            -1: u"该订单不能盘点，原因可能是：没有排产完毕，正在生产，或者已经完全发货"
        }

class MarkRefinedAction(BaseAction):
    def op(self, model):
        model.update(refined=True)
    
    def test_enabled(self, model):
        if model.refined:
            return -2
        elif not model.can_refine:
            return -3
        return 0

    def get_forbidden_msg_formats(self):
        return {
            -2: u"订单[%s]已经标记为完善", 
            -3: u"请先完善订单[%s]内容（添加子订单或者填写子订单的产品信息，完成时间），才能标记为完善",
        }

    def try_(self, preprocessed_objs):
        from litefac.permissions import CargoClerkPermission,AdminPermission
        from flask.ext.principal import Permission
        Permission.union(CargoClerkPermission, AdminPermission).test()


class NewExtraOrder(DirectAction):
    def op_upon_list(self, objs, model_view):
        return redirect(url_for("order.new_sub_order", url=request.url, _method="GET", order_id=objs[0].id))

    def test_enabled(self, model):
        from litefac.apis.order import OrderWrapper
        order = OrderWrapper(model)
        if order.measured_by_weight:
            return -2
        if order.dispatched:
            return -3
        if order.refined:
            return -4
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"只有计件类型的订单才能添加子订单", -3: u"订单%s已下发，不能添加子订单", -4: u"订单%s已完善，不能添加子订单"}

dispatch_action = DispatchAction(u"下发")
account_action = AccountAction(u"盘点")
mark_refined_action = MarkRefinedAction(u"标记为完善")
new_extra_order_action = NewExtraOrder(u"添加计件类型子订单")
