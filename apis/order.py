# -*- coding: utf-8 -*-
"""
@author: Yangminghua
"""
from datetime import datetime, date, timedelta
import sys
from flask import url_for, request
from litefac.utilities import _
from sqlalchemy import and_, or_
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import cached_property
from litefac import models
from litefac.apis import ModelWrapper
import litefac.constants as constants
from litefac.utilities import do_commit
from work_flow_repr.utils import make_tree


class OrderWrapper(ModelWrapper):
    @classmethod
    def get_list(cls, index=0, cnt=sys.maxint, after=None, customer_id=None,
                 unfinished=False, customer_order_number=None,
                 accountable_only=False, undispatched_only=False,
                 deliverable_only=False, desc=None):
        query = models.Order.query
        if accountable_only or deliverable_only:
            # 只要有一个仓单尚未发货
            query = query.filter(models.Order.sub_order_list.any(
                models.SubOrder.store_bill_list.any(
                    and_(models.StoreBill.weight > 0,
                         models.StoreBill.delivery_task_id == None))))
            if accountable_only: # 可盘点的订单要求所有的工单都已经生产完毕
                # 所有的子订单都已经排产 == 不存在子订单，其剩余质量>0
                query = query.filter(
                    ~models.Order.sub_order_list.any(
                        models.SubOrder.remaining_quantity > 0))
                # 所有的子订单的工单都已经生成完毕==不存在子订单，其有工单未完成
                query = query.filter(~models.Order.sub_order_list.any(
                    models.SubOrder.work_command_list.any(
                        models.WorkCommand.status != constants.work_command
                        .STATUS_FINISHED)))
        if undispatched_only:
            query = query.filter(~models.Order.dispatched)
        if customer_id:
            query = query.join(models.GoodsReceipt,
                               models.GoodsReceipt.id == models.Order
                               .goods_receipt_id).join(
                models.Customer,
                models.Customer.id == models.GoodsReceipt.customer_id).filter(
                models.Customer.id == customer_id)
        if after:
            query = query.filter(models.Order.create_time > after)
        if customer_order_number:
            query = query.filter(models.Order.customer_order_number.like(
                "%" + customer_order_number + "%"))
        if unfinished:
            query = query.filter(models.Order.finish_time == None).filter(
                models.Order.dispatched == True).filter(
                models.Order.sub_order_list.any(
                    or_(models.SubOrder.remaining_quantity > 0,
                        models.SubOrder.work_command_list.any(
                            models.WorkCommand.status != constants.work_command.STATUS_FINISHED))))

        count = query.count()
        if desc:
            query = query.order_by(models.Order.create_time.desc())
        query = query.offset(index).limit(cnt)
        return [OrderWrapper(order) for order in query.all()], count

    @classmethod
    def get_order(cls, order_id):
        """
        get order from database
        :return: the order with given id or None if fail
        """
        if not order_id:
            return None
        try:
            return OrderWrapper(models.Order.query.filter(
                models.Order.id == order_id).one())
        except NoResultFound:
            return None

    @classmethod
    def new_order(cls, goods_receipt_id, order_type, creator_id):
        """
        create a new order in database
        :return: the newly create order if there's corresponding goods receipt
        :raise: ValueError
        """
        from litefac.apis import cargo

        goods_receipt = cargo.get_goods_receipt(goods_receipt_id)

        try:
            creator = models.User.query.filter_by(id=creator_id).one()
        except NoResultFound:
            raise ValueError(_(u"没有此用户%d" % creator_id))

        if order_type not in (
            constants.STANDARD_ORDER_TYPE, constants.EXTRA_ORDER_TYPE):
            raise ValueError(_(u"非法的订单类型%d" % order_type))
        else:
            order = models.Order(goods_receipt=goods_receipt, creator=creator)
            do_commit(order)
            if order_type == constants.STANDARD_ORDER_TYPE:
                sub_orders = []
                for entry in goods_receipt.goods_receipt_entries:
                        sub_order = models.SubOrder(order=order,
                                                    product=entry.product,
                                                    weight=entry.weight,
                                                    pic_path=entry.pic_path,
                                                    harbor=entry.harbor,
                                                    quantity=entry.weight,
                                                    unit=u'KG',
                                                    default_harbor=entry.harbor)
                        sub_orders.append(sub_order)

                do_commit(sub_orders)
            return OrderWrapper(order)

    def __eq__(self, other):
        return isinstance(other, OrderWrapper) and other.id == self.id

    @property
    def measured_by_weight(self):
        return all(sub_order.measured_by_weight for sub_order in
                   self.sub_order_list) if self.sub_order_list else False

    @property
    def qi_weight(self):
        return sum(so.qi_weight for so in self.sub_order_list)

    @property
    def urgent(self):
        return any(sub_order.urgent for sub_order in self.sub_order_list)

    @property
    def product_list(self):
        return [sb.product for sb in self.sub_order_list]

    @property
    def net_weight(self):
        """
        即收货重量
        """
        return sum(entry.weight for entry in self.goods_receipt.goods_receipt_entries)

    @cached_property
    def remaining_weight(self):
        return sum(
            sub_order.remaining_weight for sub_order in self.sub_order_list)

    @cached_property
    def remaining_quantity(self):
        return sum(
            sub_order.remaining_quantity for sub_order in self.sub_order_list)

    @cached_property
    def delivered_weight(self):
        return sum(
            sub_order.delivered_weight for sub_order in self.sub_order_list)

    @cached_property
    def to_deliver_weight(self):
        return sum(
            sub_order.to_deliver_weight for sub_order in self.sub_order_list)

    @cached_property
    def to_deliver_store_bill_list(self):
        import itertools

        return list(
            itertools.chain.from_iterable(sub_order.to_deliver_store_bill_list for sub_order in self.sub_order_list))

    @cached_property
    def manufacturing_weight(self):
        """
        生产中重量
        """
        return sum(
            sub_order.manufacturing_weight for sub_order in self.sub_order_list
        )

    @cached_property
    def manufacturing_work_command_list(self):
        import itertools

        return list(itertools.chain.from_iterable(
            sub_order.manufacturing_work_command_list for sub_order in self.sub_order_list))

    @property
    def can_refine(self):
        from litefac.constants import DEFAULT_PRODUCT_NAME

        return self.sub_order_list and all(
            sb.due_time for sb in self.sub_order_list) and all(
            sb.product.name != DEFAULT_PRODUCT_NAME for sb in
            self.sub_order_list)

    @property
    def can_account(self):
        # 所有的子订单已经排产
        ret = all(so.remaining_quantity==0 for so in self.sub_order_list)
        # 所有子订单都已经生产完毕
        for so in self.sub_order_list:
            ret = ret and all(wc.status==constants.work_command.STATUS_FINISHED for wc in so.work_command_list)
        # 至少有一个仓单尚未发货
        ret = ret and any(any(sb.weight>0 and not sb.delivery_task for sb in so.store_bill_list) for so in self.sub_order_list)
        return ret


    @property
    def customer(self):
        return self.goods_receipt.customer

    @property
    def to_work_weight(self):
        return sum(sum(work_command.org_weight for work_command in
                       sub_order.pre_work_command_list) for sub_order in
                   self.sub_order_list)

    @property
    def done_work_command_list(self):
        ret = []
        for sub_order in self.sub_order_list:
            ret.extend(sub_order.done_work_command_list)
        return ret

    @property
    def done_work_weight(self):
        return sum(sum(work_command.processed_weight for work_command in
                       sub_order.done_work_command_list) for sub_order in self
                   .sub_order_list)

    @property
    def todo_work_cnt(self):
        return sum(len(
            sub_order.pre_work_command_list) for sub_order in self
                   .sub_order_list)

    @property
    def order_type(self):
        return self.sub_order_list[
            0].order_type if self.sub_order_list else constants \
            .EXTRA_ORDER_TYPE

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.model, k) and v not in (None, u''):
                setattr(self.model, k, v)
        do_commit(self.model)

    @property
    def warning(self):
        return self.net_weight > (self.remaining_weight + self.to_work_weight +
        self.manufacturing_weight + self.qi_weight +
        self.to_deliver_weight + self.delivered_weight)

    @property
    def url(self):
        from litefac.permissions.order import schedule_order, view_order
        if view_order.can():
            return url_for("order.order", id_=self.id, url=request.url)
        elif schedule_order.can():
            return url_for("schedule.order", id_=self.id, url=request.url)
        else:
            return ""
    @cached_property
    def qi_work_command_list(self):
        import itertools
        return list(itertools.chain.from_iterable(sub_order.qi_work_command_list for sub_order in self.sub_order_list))

    @cached_property
    def work_command_list(self):
        import itertools
        return list(itertools.chain.from_iterable(sub_order.work_command_list for sub_order in self.sub_order_list))

    def add_todo(self):
        from litefac.apis import auth, todo
        for to in auth.get_user_list(constants.groups.SCHEDULER):
            todo.new_todo(to, todo.DISPATCH_ORDER, self)

    @property
    def log_list(self):
        from litefac.apis.log import LogWrapper

        ret = LogWrapper.get_log_list(str(self.id), self.model.__class__.__name__)
        for sub_order in self.sub_order_list:
            ret.extend(sub_order.log_list)
        return sorted(ret, lambda a, b: cmp(a.create_time, b.create_time), reverse=True)

    @property
    def work_flow_json(self):
        try:
            return make_tree(self.goods_receipt)
        except AttributeError, e:
            raise Exception(e.message)


class SubOrderWrapper(ModelWrapper):

    @classmethod
    def new_sub_order(cls, **kwargs):
        """新建计件类型的子订单。
        """
        order = get_order(kwargs["order_id"])
        if not order:
            raise ValueError(_(u'订单%d不存在') % kwargs["order_id"])

        try:
            harbor = models.Harbor.query.filter(
                models.Harbor.name == kwargs["harbor_name"]).one()
        except NoResultFound:
            raise ValueError(_(u'装卸点%(harbor)s不存在') % kwargs["harbor_name"])

        try:
            product = models.Product.query.filter(
                models.Product.id == kwargs["product_id"]).one()
        except NoResultFound:
            raise ValueError(_(u'产品%(product_id)不存在') % kwargs["product_id"])

        sb = models.SubOrder(harbor=harbor,
                             product=product,
                             spec=kwargs["spec"],
                             type=kwargs["type"],
                             order=order,
                             urgent=kwargs["urgent"],
                             returned=kwargs["returned"],
                             tech_req=kwargs["tech_req"],
                             quantity=kwargs["quantity"],
                             unit=kwargs["unit"],
                             due_time=kwargs["due_time"],
                             order_type=constants.EXTRA_ORDER_TYPE,
                             weight=kwargs["weight"])

        return SubOrderWrapper(do_commit(sb))

    @property
    def goods_receipt(self):
        return self.order.goods_receipt

    @property
    def customer(self):
        return self.goods_receipt.customer

    @property
    def measured_by_weight(self):
        return self.order_type == constants.STANDARD_ORDER_TYPE

    @property
    def pic_url(self):
        if self.pic_path:
            return url_for("serv_pic", filename=self.pic_path)
        else:
            return ""

    @classmethod
    def get_sub_order(cls, sub_order_id):
        if not sub_order_id:
            return None
        try:
            return SubOrderWrapper(
                models.SubOrder.query.filter_by(
                    id=sub_order_id).one())
        except NoResultFound:
            return None

    def update(self, **kwargs):
        if self.model.order.dispatched:
            raise ValueError(u"已下发的订单不能再修改")
        for k, v in kwargs.items():
            if hasattr(self.model, k) and v != u'':
                if k.__eq__("due_time"):
                    setattr(self.model, k, datetime.strptime(v, '%Y-%m-%d'))
                    continue
                setattr(self.model, k, v)
                if k.__eq__(
                        "weight") and self.order_type == constants.STANDARD_ORDER_TYPE:
                    setattr(self.model, "quantity", v)
                if k.__eq__("quantity") and not self.model.order.dispatched:
                    self.model.remaining_quantity = v
        do_commit(self.model)

    def end(self):
        self.model.finish_time = datetime.now()
        do_commit(self.model)

    def delete(self):
        do_commit(self.model, "delete")

    def __eq__(self, other):
        return isinstance(other, SubOrderWrapper) and other.id == self.id

    @cached_property
    def pre_work_command_list(self):
        return [work_command for work_command in self.work_command_list if
                work_command.status in (
                constants.work_command.STATUS_DISPATCHING,
                constants.work_command.STATUS_REFUSED)]

    @cached_property
    def manufacturing_work_command_list(self):
        manufacturing_status_set = {constants.work_command.STATUS_ASSIGNING,
                                    constants.work_command.STATUS_ENDING,
                                    constants.work_command.STATUS_LOCKED}
        return [work_command for work_command in self.work_command_list if
                work_command.status in manufacturing_status_set]

    @property
    def qi_work_command_list(self):
        return [work_command for work_command in self.work_command_list if
            work_command.status == constants.work_command.STATUS_QUALITY_INSPECTING]

    @cached_property
    def done_work_command_list(self):
        return [work_command for work_command in self.work_command_list if
                work_command.status == constants.work_command
                .STATUS_FINISHED and work_command.procedure and (
                not work_command.parent_qir or work_command.parent_qir.result == constants.quality_inspection.FINISHED)]

    @cached_property
    def remaining_weight(self):
        """
        未预排产重量
        """
        return self.remaining_quantity * self.weight / self.quantity

    @cached_property
    def delivered_weight(self):
        ret = {}
        for sb in self.store_bill_list:
            if sb.delivery_task_id:
                ret.setdefault(sb.delivery_task_id, sb.delivery_task)
        return sum(dt.weight for dt in ret.values())

    @cached_property
    def manufacturing_weight(self):
        return sum(
            work_command.org_weight for work_command in self
            .manufacturing_work_command_list)

    @property
    def qi_weight(self):
        return sum(work_command.processed_weight for work_command in self.qi_work_command_list)

    @cached_property
    def to_deliver_weight(self):
        return sum(store_bill.weight for store_bill in self.to_deliver_store_bill_list)

    @cached_property
    def to_deliver_store_bill_list(self):
        return [store_bill for store_bill in self.store_bill_list if not store_bill.delivery_task_id]

    @property
    def log_list(self):
        from litefac.apis.log import LogWrapper

        ret = LogWrapper.get_log_list(str(self.id), self.model.__class__.__name__)
        return sorted(ret, lambda a, b: cmp(a.create_time, b.create_time), reverse=True)


def get_order_type_list():
    t1 = dict(id=constants.STANDARD_ORDER_TYPE,
              name=constants.STANDARD_ORDER_TYPE_NAME)
    t2 = dict(id=constants.EXTRA_ORDER_TYPE,
              name=constants.EXTRA_ORDER_TYPE_NAME)
    return [t1, t2]


def get_customer_list(time_span, dispatched=False):
    """
    获取指定时间段内有订单的客户
    """
    cst_q = models.Customer.query.join(models.GoodsReceipt).join(
        models.Order)
    if dispatched:
        customers = cst_q.filter(models.Order.dispatched == True).filter(
            models.Order.finish_time == None).distinct()
    else:
        should_after = get_should_after_date(time_span)
        customers = cst_q.filter(
            models.Order.create_time > should_after).distinct()
    return customers


def get_should_after_date(time_span):
    if time_span == "day":
        # date类型的str方法能够自动按照ISO_8601转换为字符串。而且，sqlalchemy
        # 能够将这种字符串转换为时间
        should_after = date.today()
    elif time_span == "week":
        should_after = date.today() - timedelta(7)
    elif time_span == "month":
        should_after = date.today() - timedelta(30)
    else: # 不限时间，那么我们不加此限制
        should_after = date.fromtimestamp(0L)
    return should_after


new_order = OrderWrapper.new_order
get_order = OrderWrapper.get_order
get_order_list = OrderWrapper.get_list
get_sub_order = SubOrderWrapper.get_sub_order

if __name__ == "__main__":
    pass
