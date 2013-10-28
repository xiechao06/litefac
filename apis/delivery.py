# -*- coding:UTF-8 -*-
import time
import sys
from datetime import datetime
from collections import OrderedDict

from flask import url_for, render_template
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import cached_property
import yawf

from litefac import models, constants
import litefac.apis.order
from litefac import database
from litefac.database import db
import litefac.apis.customer
from litefac.apis import ModelWrapper
from litefac.utilities import do_commit, to_timestamp


class DeliverySessionWrapper(ModelWrapper):
    @property
    def deleteable(self):
        return not bool(self.delivery_task_list)

    @property
    def is_locked(self):
        return bool(self.delivery_task_list and
                    any(not t.weight for t in self.delivery_task_list) or 
                    yawf.token_bound(constants.work_flow.DELIVERY_TASK_WITH_ABNORMAL_WEIGHT, str(self.id)))

    @property
    def load_finish(self):
        return bool(self.finish_time)

    @cached_property
    def customer_list(self):
        return list(set([task.customer for task in self.delivery_task_list]))

    @cached_property
    def customer_id_list(self):
        return list(set([task.customer.id for task in self.delivery_task_list]))

    @property
    def with_person_des(self):
        return u'是' if self.with_person else u'否'

    @cached_property
    def need_store_bill(self):
        return not self.finish_time and (not self.store_bill_list or all(
            store_bill.delivery_task for store_bill in
            self.store_bill_list))

    def __repr__(self):
        return u"<DeliverySession id:(%d) plate:(%r) tare:(%d) create_time:(" \
               u"%s) finish_time:(%s)>" % (
                   self.id, self.plate, self.tare,
                   self.create_time.strftime("%Y-%m-%d[%H:%M:%S]"),
                   self.finish_time.strftime(
                       "%Y-%m-%d[%H:%M:%S]") if self.finish_time else "-")

    @classmethod
    def new_delivery_session(cls, plate, tare, with_person=False):
        """create delivery session
        :param cls:
        :param plate:
        :param tare:
        :return:a newly delivery session
        """
        plate = plate.upper()
        try:
            models.Plate.query.filter(
                models.Plate.name == plate).one()
        except NoResultFound:
            do_commit(models.Plate(name=plate))
        return DeliverySessionWrapper(
            do_commit(models.DeliverySession(plate, tare, with_person)))

    def update(self, **kwargs):
        if kwargs.get("store_bill_list"):
            models.StoreBill.query.filter(
                models.StoreBill.id.in_(kwargs.get("store_bill_list"))).update(
                {"delivery_session_id": self.id},
                synchronize_session='fetch')
            db.session.commit()
        if kwargs.has_key("finish_time"):
            if kwargs.get("finish_time"):
                models.StoreBill.query.filter(
                    models.StoreBill.delivery_session_id == self.id,
                    models.StoreBill.delivery_task_id == None).update(
                    {"delivery_session_id": None})
                self.model.finish_time = datetime.fromtimestamp(
                    kwargs["finish_time"])
                db.session.add(self.model)
            else:
                self.model.finish_time = None
                db.session.add(self.model)
            db.session.commit()

    def add_store_bill_list(self, store_bill_id_list):
        if store_bill_id_list:
            models.StoreBill.query.filter(
                models.StoreBill.id.in_(store_bill_id_list)).update(
                {"delivery_session_id": self.id}, synchronize_session='fetch')
            db.session.commit()

        else:
            raise ValueError(u'至少要有一个仓单')

    @property
    def can_finish(self):
        return not self.finish_time and all(
            ut.weight for ut in self.delivery_task_list)

    def finish(self):
        if self.can_finish:
            self.update(finish_time=time.time())
            return True
        return False

    def reopen(self):
        if self.finish_time:
            self.update(finish_time=None)
            return True
        return False

    @cached_property
    def stale(self):
        return len(self.consignment_list) != len(self.customer_list) or any(cn.stale for cn in self.consignment_list)

    def gc_consignment_list(self):
        """
        delete the consignment which has not entry converted from current
        delivery_session's delivery_task
        """
        for cn in self.consignment_list:
            if cn.customer.id not in self.customer_id_list:
                do_commit(cn.model, "delete")

    @property
    def log_list(self):
        from litefac.models import Log

        ret = Log.query.filter(Log.obj_pk == str(self.id)).filter(
            Log.obj_cls == self.model.__class__.__name__).all()
        for task in self.delivery_task_list:
            ret.extend(task.log_list)
        return sorted(ret, lambda a, b: cmp(a.create_time, b.create_time), reverse=True)

class DeliveryTaskWrapper(ModelWrapper):
    @classmethod
    def new_delivery_task(cls, actor_id, finished_store_bill_list,
                          unfinished_store_bill, remain=None):
        """
        创建一个新的卸货任务，若有部分完成的仓单，需要将没有完成的部分生成一个新的仓单, 这个仓单是完成的
        :param cls:
        :param actor_id:
        :param finished_store_bill_id_list:
        :param unfinished_store_bill_id:
        :param remain:
        :return:
        """
        if unfinished_store_bill and not remain:
            raise ValueError(u"需要remain字段")
        if unfinished_store_bill:
            # 创建一个已经完成的新仓单
            new_sb = models.StoreBill(unfinished_store_bill.qir)
            new_sb.quantity = max(1,
                                  unfinished_store_bill.quantity - remain)
            new_sb.weight = int(
                unfinished_store_bill.unit_weight * new_sb.quantity)
            new_sb.delivery_session = unfinished_store_bill.delivery_session
            new_sb.printed = True
            finished_store_bill_list.append(new_sb)
            # 重新计算未完成仓单的数量，重量, 并且加入到已有的完成仓单列表中
            new_sb.harbor = unfinished_store_bill.harbor
            # 必须先计算净重
            unfinished_store_bill.weight = int(
                unfinished_store_bill.unit_weight * remain)
            unfinished_store_bill.quantity = remain
            unfinished_store_bill.delivery_session = None

        if len(finished_store_bill_list) == 0:
            raise ValueError(u"至少需要一个仓单")
        ds = finished_store_bill_list[0].delivery_session
        dt = models.DeliveryTask(ds, actor_id)
        actor = models.User.query.get(actor_id)
        for sb in finished_store_bill_list:
            sb.delivery_task = dt
        dt.quantity = sum(sb.quantity for sb in finished_store_bill_list)

        dt.returned_weight = sum(
            sb.weight for sb in finished_store_bill_list if sb.sub_order.returned)
        if unfinished_store_bill:
            do_commit([unfinished_store_bill, dt] + finished_store_bill_list)
            StoreBillWrapper(new_sb).do_create_log(
                u"由剩余%s公斤的仓单%s装货、分裂产生" % (unfinished_store_bill.weight, unfinished_store_bill.id), actor=actor)
            StoreBillWrapper(new_sb).do_update_log(u"装货，发货会话%s、发货任务%s" % (ds.id, dt.id))
            StoreBillWrapper(unfinished_store_bill).do_update_log(u"装货、分裂出%s公斤的仓单%s" % (new_sb.weight, new_sb.id),
                                                                  actor=actor)
        else:
            do_commit([dt] + finished_store_bill_list)
        for sb in finished_store_bill_list:
            StoreBillWrapper(sb).do_update_log(u"装货，发货会话%s、发货任务%s" % (ds.id, dt.id))

        from litefac.apis.todo import new_todo, WEIGH_DELIVERY_TASK
        from litefac.apis.auth import get_user_list

        for to in get_user_list(constants.groups.CARGO_CLERK):
            new_todo(to, WEIGH_DELIVERY_TASK, dt)
        dt = DeliveryTaskWrapper(dt)
        if dt.consignment:
            dt.consignment.staled()
        return dt

    @property
    def store_bill_id_list(self):
        return [sb.id for sb in self.store_bill_list]

    @property
    def log_list(self):
        from litefac.models import Log

        ret = Log.query.filter(Log.obj_pk == str(self.id)).filter(
            Log.obj_cls == self.model.__class__.__name__).all()
        return sorted(ret, lambda a, b: cmp(a.create_time, b.create_time), reverse=True)

    @property
    def pic_url_list(self):
        return [store_bill.pic_url for store_bill in self.store_bill_list if store_bill.pic_url]

    @cached_property
    def last_weight(self):
        session = get_delivery_session(self.delivery_session_id)
        idx = get_delivery_session(
            self.delivery_session_id).delivery_task_list.index(self)
        if idx <= 0:
            return session.tare
        else:
            last_task = session.delivery_task_list[idx - 1]
            return last_task.weight + last_task.last_weight

    @classmethod
    def get_delivery_task(cls, task_id):
        if not task_id:
            return None
        try:
            return DeliveryTaskWrapper(
                models.DeliveryTask.query.filter_by(
                    id=task_id).one())
        except NoResultFound:
            return None

    def update(self, **kwargs):
        if kwargs.get("weight"):
            self.weight = kwargs['weight']

            total_org_weight = float(
                sum([sb.weight for sb in self.store_bill_list]))
            for sb in self.store_bill_list:
                sb.model.weight = int(
                    round(self.weight * sb.weight / total_org_weight))
                from litefac import constants

                if sb.sub_order.order_type == constants.STANDARD_ORDER_TYPE:
                    sb.model.quantity = sb.model.weight
            if self.consignment:
                self.consignment.staled()
        elif kwargs.get("returned_weight"):
            self.model.returned_weight = kwargs["returned_weight"]
            if self.consignment:
                self.consignment.staled()
            # 这也说明，若是计件类型的仓单，数量不会根据称重进行调整
        elif kwargs.get("is_last"):
            self.model.is_last = kwargs["is_last"]
        do_commit(self.model)
        return self

    def __eq__(self, other):
        return isinstance(other, DeliveryTaskWrapper) and other.id == self.id

    @property
    def consignment(self):
        for consignment in self.delivery_session.consignment_list:
            if consignment.customer.id == self.customer.id:
                return consignment
        return None

    @property
    def team_list(self):
        from litefac.utilities.functions import deduplicate

        return deduplicate(
            [sb.qir.work_command.team for sb in self.store_bill_list],
            lambda x: x.model)

    @property
    def sub_order_list(self):
        from litefac.utilities.functions import deduplicate

        return deduplicate([sb.sub_order for sb in self.store_bill_list],
                           lambda x: x.model)

    @property
    def spec_type_list(self):
        return ["-".join((sub_order.spec, sub_order.type)) for sub_order in
                self.sub_order_list if sub_order.spec or sub_order.type]

    @property
    def unit(self):
        if self.sub_order_list:
            return self.sub_order_list[0].unit
        else:
            return ""

    def delete(self):
        ds = self.delivery_session
        do_commit(self.model, "delete")
        from litefac.portal.delivery.fsm import fsm

        fsm.reset_obj(ds)
        from flask.ext.login import current_user
        from litefac.basemain import timeline_logger

        timeline_logger.info(u"删除了发货任务%d" % self.id,
                             extra={"obj": self.delivery_session.model,
                                    "obj_pk": self.delivery_session.id,
                                    "action": u"删除发货任务",
                                    "actor": current_user})
        fsm.next(constants.delivery.ACT_WEIGHT, current_user)

        from litefac.apis import todo
        # delete todo
        todo.remove_todo(todo.WEIGH_DELIVERY_TASK, self.id)
        return True


class ConsignmentWrapper(ModelWrapper):
    @classmethod
    def get_list(cls, delivery_session_id=None, is_paid=None,
                 exporting=False, pay_in_cash=False, customer_id=0, idx=0,
                 cnt=sys.maxint):
        cons_q = models.Consignment.query
        if is_paid is not None:
            cons_q = cons_q.filter(
                models.Consignment.is_paid == is_paid)
        if pay_in_cash:
            cons_q = cons_q.filter(
                models.Consignment.pay_in_cash == True)
        if delivery_session_id:
            cons_q = cons_q.filter(
                models.Consignment.delivery_session_id == delivery_session_id)
        if exporting:
            cons_q = cons_q.filter(models.Consignment.MSSQL_ID == None)
        if customer_id:
            cons_q = cons_q.filter(models.Consignment.customer_id == customer_id)
        totalcnt = cons_q.count()
        return [ConsignmentWrapper(c) for c in
                cons_q.offset(idx).limit(cnt).all()], totalcnt

    @cached_property
    def measured_by_weight(self):
        sub_order_list = []
        for task in self.delivery_session.delivery_task_list:
            sub_order_list.extend(task.sub_order_list)
        return all(
            sub_order.measured_by_weight for sub_order in sub_order_list)

    @classmethod
    def get_consignment(cls, id_):
        if not id_:
            return None
        try:
            return ConsignmentWrapper(
                models.Consignment.query.filter_by(id=id_).one())
        except NoResultFound:
            return None

    @classmethod
    def create_or_update_consignment(cls, customer_id, delivery_session_id, pay_in_cash):
        try:
            consignment = ConsignmentWrapper(models.Consignment.query.filter(models.Consignment.customer_id == customer_id).filter(
                models.Consignment.delivery_session_id == delivery_session_id).one())
            if consignment.stale:
                consignment.add_product_entries()
                consignment.add_todo()
        except NoResultFound:
            return new_consignment(customer_id, delivery_session_id, pay_in_cash=pay_in_cash)

    def add_product_entries(self):
        self.product_list = []
        do_commit(self)
        for t in self.delivery_session.delivery_task_list:
            if t.customer.id == self.customer_id:
                self.add_product_entry(t)

    def add_product_entry(self, delivery_task):
        p = models.ConsignmentProduct(delivery_task.product, delivery_task, self)
        if delivery_task.team_list:
            p.team = delivery_task.team_list[0]
        p.weight = delivery_task.weight
        p.returned_weight = delivery_task.returned_weight
        if not delivery_task.quantity:
            delivery_task.quantity = sum(store_bill.quantity for store_bill in
                                         delivery_task.store_bill_list)
        p.quantity = delivery_task.quantity
        if delivery_task.sub_order_list:
            sb = delivery_task.sub_order_list[0]
            p.unit = sb.unit
            p.spec = sb.spec
            p.type = sb.type
        do_commit(p)

    def staled(self):
        self.stale = True
        do_commit(self.model)

    @classmethod
    def new_consignment(cls, customer_id, delivery_session_id, pay_in_cash):
        customer = litefac.apis.customer.get_customer(customer_id)
        if not customer:
            raise ValueError(u'没有此客户%d' % customer_id)
        delivery_session = litefac.apis.delivery.get_delivery_session(
            delivery_session_id)
        if not delivery_session:
            raise ValueError(u'没有此发货会话%d' % delivery_session_id)
        if customer not in set(task.customer for task in delivery_session.delivery_task_list):
            raise ValueError("delivery session %d has no customer %s" % (delivery_session_id, customer.name))
        consignment = ConsignmentWrapper(do_commit(models.Consignment(customer, delivery_session, pay_in_cash)))
        from flask.ext.login import current_user
        if current_user.is_authenticated():
            consignment.actor = current_user
        consignment.add_product_entries()
        consignment.add_todo()
        return consignment

    def remove_todo(self):
        litefac.apis.todo.remove_todo(litefac.apis.todo.PAY_CONSIGNMENT, self.id)

    def add_todo(self):
        self.remove_todo()
        if self.pay_in_cash and not self.is_paid:
            for to in litefac.apis.auth.get_user_list(constants.groups.ACCOUNTANT):
                litefac.apis.todo.new_todo(to, litefac.apis.todo.PAY_CONSIGNMENT, self)

    @property
    def plate(self):
        return self.delivery_session.plate

    @classmethod
    def update(cls, id, **kwargs):
        consignment = ConsignmentWrapper.get_consignment(id)
        if consignment.MSSQL_ID:
            raise ValueError(u"已导入原系统的发货单不能再修改")
        for k, v in kwargs.items():
            if hasattr(consignment, k):
                setattr(consignment, k, v)
                if k == "pay_in_cash" and v and not consignment.pay_in_cash:
                    consignment.add_todo()
        return ConsignmentWrapper(do_commit(consignment))

    def paid(self):
        self.model.is_paid = True
        do_commit(self.model)

    @classmethod
    def get_customer_list(cls):
        from litefac import apis

        return apis.customer.CustomerWrapper.get_customer_list(models.Consignment)

    @cached_property
    def delivery_task_list(self):
        task_list = []
        for task in self.delivery_session.delivery_task_list:
            if task.customer.id == self.customer.id:
                task_list.append(task)
        return task_list


class ConsignmentProductWrapper(ModelWrapper):
    @classmethod
    def get_product(cls, id_):
        current = models.ConsignmentProduct.query.get(id_)
        if current:
            return ConsignmentProductWrapper(current)
        else:
            return None

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.model, k):
                setattr(self.model, k, v)
        do_commit(self.model)


class StoreBillWrapper(ModelWrapper):
    @property
    def delivered(self):
        return bool(self.delivery_task)

    @property
    def pic_url(self):
        if self.qir.pic_path:
            return url_for("serv_pic", filename=self.qir.pic_path)
        else:
            return ""

    @cached_property
    def product(self):
        return self.sub_order.product

    @property
    def product_name(self):
        return self.product.name

    @property
    def unit(self):
        return self.sub_order.unit

    @classmethod
    def get_store_bill(cls, store_bill_id):
        if not store_bill_id:
            return None
        try:
            return StoreBillWrapper(models.StoreBill.query.filter_by(id=store_bill_id).one())
        except NoResultFound:
            return None

    @classmethod
    def customer_bill_list(cls):
        store_bill_list = get_store_bill_list()[0]

        from itertools import groupby
        from operator import attrgetter

        getter = attrgetter("customer.name")

        customer_list = []
        for k, g in groupby(sorted(store_bill_list, key=lambda x: getter(x).encode("gbk")),
                            lambda x: getattr(x, "customer")):
            k.store_bill_list = list(g)
            customer_list.append(k)

        return customer_list

    @classmethod
    def update_store_bill(cls, store_bill_id, **kwargs):
        store_bill = StoreBillWrapper.get_store_bill(store_bill_id)
        if not store_bill:
            raise ValueError(u'没有此仓单%d' % store_bill_id)

        if kwargs.get("printed", None):
            store_bill.model.printed = kwargs.get("printed")

        if kwargs.get("harbor"):
            try:
                harbor = models.Harbor.query.filter_by(
                    name=kwargs.get("harbor")).one()
            except NoResultFound:
                raise ValueError(u'没有此装卸点%s' % kwargs.get("harbor"))
            store_bill.model.harbor = harbor

        if kwargs.get("delivery_session_id"):
            store_bill.delivery_session_id = kwargs.get("delivery_session_id")
            store_bill.delivery_task_id = kwargs.get("delivery_task_id")
        if kwargs.get("weight"):
            store_bill.weight = kwargs["weight"]
        if kwargs.get("quantity"):
            store_bill.quantity = kwargs["quantity"]
        do_commit(store_bill.model)
        store_bill.do_update_log()
        return StoreBillWrapper(do_commit(store_bill))

    @property
    def log_list(self):
        from litefac.apis.log import LogWrapper

        ret = LogWrapper.get_log_list(str(self.id), self.model.__class__.__name__)
        return sorted(ret, lambda a, b: cmp(a.create_time, b.create_time), reverse=True)

    def do_create_log(self, message="", actor=None):
        from flask.ext.login import current_user
        from litefac.basemain import timeline_logger
        timeline_logger.info(message or u"创建仓单%d" % self.id,
                             extra={"obj": self.model,
                                    "obj_pk": self.id,
                                    "action": u"创建",
                                    "actor": actor or (current_user if current_user.is_authenticated() else None)})

    def do_update_log(self, message="", actor=None):
        from flask.ext.login import current_user
        from litefac.basemain import timeline_logger

        timeline_logger.info(message or u"更新仓单%d" % self.id,
                             extra={"obj": self.model,
                                    "obj_pk": self.id,
                                    "action": u"更新",
                                    "actor": actor or (current_user if current_user.is_authenticated() else None)})

    @property
    def previous_store_bill(self):
        if self.qir.store_bill_list and self.qir.store_bill_list[0].id != self.id:
            return self.qir.store_bill_list[0]
        return None

    @property
    def next_store_bill_list(self):
        if self.qir.store_bill_list and self.qir.store_bill_list[0].id == self.id:
            return [sb for sb in self.qir.store_bill_list if sb.id != self.id]
        return []

def get_delivery_session_list(idx=0, cnt=sys.maxint, unfinished_only=False,
                              keywords=None):
    q = models.DeliverySession.query.filter(
        models.DeliverySession.plate != "foo")
    if unfinished_only:
        q = q.filter(models.DeliverySession.finish_time == None).join(
            models.StoreBill).filter(models.StoreBill.delivery_task == None)
    if keywords:
        q = q.join(models.DeliveryTask).join(models.StoreBill).join(
            models.Customer).filter(
            or_(models.DeliverySession.plate.like("%" + keywords + "%"),
                models.Customer.name.like("%" + keywords + "%")))
    total_cnt = q.count()
    return [DeliverySessionWrapper(ds) for ds in
            q.order_by(models.DeliverySession.create_time.desc()).offset(
                idx).limit(cnt).all()], total_cnt

def get_delivery_session(session_id):
    if not session_id:
        return None
    try:
        return DeliverySessionWrapper(models.DeliverySession.query.filter(
            models.DeliverySession.id == session_id).one())
    except NoResultFound:
        return None

def get_delivery_task_list(ds_id):
    return [DeliveryTaskWrapper(dt) for dt in
            models.DeliveryTask.query.filter_by(
                delivery_session_id=ds_id).all()]

def create_or_update_consignment(customer_id, delivery_session_id, pay_in_cash):
    try:
        cn = ConsignmentWrapper(models.Consignment.query.filter(
            models.Consignment.customer_id == customer_id).filter(
            models.Consignment.delivery_session_id == delivery_session_id).one())
        cn.pay_in_cash = pay_in_cash
        if cn.stale:
            cn.add_product_entries()
            cn.stale = False
        do_commit(cn)
        return cn
    except NoResultFound:
        return new_consignment(customer_id, delivery_session_id, pay_in_cash=pay_in_cash)

def get_store_bill_list(idx=0, cnt=sys.maxint, unlocked_only=True, qir_id=None,
                        customer_id="", delivery_session_id=None,
                        printed_only=False, unprinted_only=False,
                        should_after=None):
    # TODO 没有彻底测试
    q = models.StoreBill.query
    if delivery_session_id:
        q = q.filter(
            models.StoreBill.delivery_session_id == delivery_session_id)
    elif unlocked_only:
        q = q.filter(models.StoreBill.delivery_session_id == None)
    if qir_id:
        q = q.filter(models.StoreBill.qir_id == qir_id)
    if customer_id:
        q = q.filter(models.StoreBill.customer_id == customer_id)
    if printed_only:
        q = q.filter(models.StoreBill.printed == True)
    if unprinted_only:
        q = q.filter(models.StoreBill.printed == False)
    if should_after:
        # note, remember to included in ""
        q = q.filter(models.StoreBill.create_time > should_after)

    total_cnt = q.count()
    q = q.order_by(models.StoreBill.id.desc()).offset(idx).limit(cnt)
    return [StoreBillWrapper(sb) for sb in q.all()], total_cnt

def fake_delivery_task():
    fake_delivery_session = do_commit(models.DeliverySession(plate="foo", tare=0, finish_time=datetime.now()))
    return do_commit(models.DeliveryTask(fake_delivery_session, None))

new_delivery_session = DeliverySessionWrapper.new_delivery_session
get_consignment_list = ConsignmentWrapper.get_list
get_consignment = ConsignmentWrapper.get_consignment
new_consignment = ConsignmentWrapper.new_consignment
new_delivery_task = DeliveryTaskWrapper.new_delivery_task
get_delivery_task = DeliveryTaskWrapper.get_delivery_task
get_store_bill = StoreBillWrapper.get_store_bill
get_store_bill_customer_list = StoreBillWrapper.customer_bill_list
update_store_bill = StoreBillWrapper.update_store_bill

def store_bill_remain_unacceptable(unfinished_store_bill, remain):
    return remain >= unfinished_store_bill.weight


class CreateDeliveryTaskWithAbnormalWeight(yawf.Policy):

    def __call__(self):
        # strong guaranteed here
        doc = database.codernity_db.get('id', self.node.tag, with_doc=True)
        delivery_session = get_delivery_session(doc['delivery_session_id'])
        remain = doc['remain']
        from litefac.apis import wraps
        finished_store_bill_list = [wraps(models.StoreBill.query.get(store_bill_id)) for store_bill_id in doc['finished_store_bill_id_list']]
        unfinished_store_bill = wraps(models.StoreBill.query.get(doc['unfinished_store_bill_id']))
        is_finished = doc['is_last_task']
        loader = models.User.query.get(doc['loader_id'])
        from litefac.portal.delivery_ws.webservices import create_delivery_task
        create_delivery_task(delivery_session, remain, finished_store_bill_list, 
                             unfinished_store_bill, loader, is_finished)

    @property
    def dependencies(self):
        return [('PermitDeliveryTaskWithAbnormalWeight', 
                     {'name': u'批准生成剩余重量异常的发货任务',
                     'handler_group': models.Group.query.filter(models.Group.id==constants.groups.CARGO_CLERK).one(),
                     'tag': self.node.tag,})]


    def on_delayed(self, unmet_node):
    
        from litefac.apis.todo import new_todo, PERMIT_DELIVERY_TASK_WITH_ABNORMAL_WEIGHT
        from litefac.apis.auth import get_user_list
        for user in get_user_list(unmet_node.handler_group_id):
            new_todo(user, PERMIT_DELIVERY_TASK_WITH_ABNORMAL_WEIGHT, unmet_node)

class PermitDeliveryTaskWithAbnormalWeight(yawf.Policy):

    @property
    def annotation(self):
        from litefac.apis import wraps
        doc = database.codernity_db.get('id', self.node.tag, with_doc=True)
        remain = doc['remain']
        unfinished_store_bill = wraps(models.StoreBill.query.get(doc['unfinished_store_bill_id']))
        d = OrderedDict()
        d[u'剩余仓单编号'] = unfinished_store_bill.id
        d[u'仓单原重'] = unfinished_store_bill.weight
        d[u'产品'] = unfinished_store_bill.sub_order.product.name + '(%s:%s)' % (unfinished_store_bill.sub_order.spec or '?',
                                                                            unfinished_store_bill.sub_order.type or '?')
        d[u'客户'] = unfinished_store_bill.sub_order.customer.name
        d[u'剩余重量'] = str(remain) + u'(公斤)'
        return d

if __name__ == "__main__":
    pass
