# -*- coding:UTF-8 -*-
import sys
from flask import url_for
from flask.ext.babel import _
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import cached_property
from litefac import models, constants
from litefac.apis import ModelWrapper
from litefac.utilities import do_commit


g_status_desc = {
    constants.cargo.STATUS_LOADING: u"正在卸货",
    constants.cargo.STATUS_WEIGHING: u"等待称重",
    constants.cargo.STATUS_CLOSED: u"关闭",
    constants.cargo.STATUS_DISMISSED: u"取消",
}


class UnloadSessionWrapper(ModelWrapper):
    @property
    def deleteable(self):
        return not bool(self.task_list)

    @property
    def is_locked(self):
        return bool(
            self.task_list and any(not t.weight for t in self.task_list))

    @property
    def load_finish(self):
        return bool(self.finish_time)

    @property
    def finished(self):
        """
        已经关闭，并且所有的unload task都已经称重, 注意与closeable的区别
        """
        return bool(
            self.finish_time and all(t.weight for t in self.task_list))

    # @property
    # def status(self):
    #     if self.finish_time:
    #         if len(self.customer_list) > len(self.goods_receipt_list):
    #             return u"待生成收货单"
    #         else:
    #             return u"已完成"
    #     else:
    #         if self.task_list and not all(t.weight for t in self.task_list):
    #             return u"待称重"
    #         else:
    #             return u"待卸货"

    @property
    def status_desc(self):
        return g_status_desc.get(self.status) or u"未知"

    @cached_property
    def customer_list(self):
        return list(set([task.customer for task in self.task_list]))

    @cached_property
    def customer_id_list(self):
        return [customer.id for customer in self.customer_list]

    @property
    def closeable(self):
        return not self.finish_time and all(ut.weight for ut in self.task_list)

    @property
    def closed(self):
        """
        已经关闭（不能再添加unload task）
        """
        return bool(self.finish_time)

    @property
    def log_list(self):
        from litefac.apis.log import LogWrapper

        ret = LogWrapper.get_log_list(str(self.id), self.model.__class__.__name__)
        for task in self.task_list:
            ret.extend(task.log_list)
        return sorted(ret, lambda a, b: cmp(a.create_time, b.create_time))

    @property
    def with_person_des(self):
        return u'是' if self.with_person else u'否'

    def __repr__(self):
        s_create_time = self.create_time.strftime("%Y-%m-%d[%H:%M:%S]")
        s_finish_time = self.finish_time.strftime("%Y-%m-%d[%H:%M:%S]") \
            if self.finish_time else "-"
        return "<UnloadSession (%d) (%r) (%d) (%s) (%s)>" % (self.id,
                                                             self.plate,
                                                             self.gross_weight,
                                                             s_create_time,
                                                             s_finish_time)


    def update(self, finish_time):
        """
        update the unload session's scalar attribute persistently
        only finish_time could be updated
        :return: the updated unload session if succeed, otherwise None
        """
        self.model.finish_time = finish_time
        do_commit(self.model)

    def gc_goods_receipts(self):
        """
        delete the goods_receipt which has not entry converted from current
        unload_session's unload_task_list
        """
        for gr in self.goods_receipt_list:
            if gr.customer.id not in self.customer_id_list:
                do_commit(gr.model, "delete")


    def clean_goods_receipts(self):
        """
        Iterator the customers and create a goods_receipt.
        Then delete the unnecessary goods_receipts.
        """
        for id_ in self.customer_id_list:
            create_or_update_goods_receipt(unload_session_id=self.id,
                                                      customer_id=id_)

        self.gc_goods_receipts()

    @cached_property
    def goods_receipt_stale(self):
        return any(gr.stale for gr in self.goods_receipt_list)


class UnloadTaskWrapper(ModelWrapper):
    @property
    def pic_url(self):
        if self.pic_path:
            return url_for("serv_pic", filename=self.pic_path)
        else:
            return ""

    @property
    def log_list(self):
        from litefac.apis.log import LogWrapper

        return LogWrapper.get_log_list(str(self.id), self.model.__class__.__name__)

    def update(self, **kwargs):
        """
        update scalar attributes of unload task in database
        only **weight** and **product_id** allowed
        """
        if kwargs.get("weight"):
            self.model.weight = kwargs["weight"]
        if kwargs.get("product_id"):
            try:
                self.model.product = models.Product.query.filter(
                    models.Product.id == kwargs["product_id"]).one()
            except NoResultFound:
                raise ValueError(u"无此产品%s" % kwargs["product_id"])
        if kwargs.get("customer"):
            self.model.customer = kwargs["customer"]
        do_commit(self.model)

    @property
    def last_weight(self):
        idx = self.unload_session.task_list.index(self)
        if idx <= 0:
            return self.unload_session.gross_weight
        else:
            last_task = self.unload_session.task_list[idx - 1]
            return last_task.last_weight - last_task.weight

    def __eq__(self, other):
        return isinstance(other, UnloadTaskWrapper) and other.id == self.id

    @cached_property
    def goods_receipt(self):
        for goods_receipt in self.unload_session.goods_receipt_list:
            if goods_receipt.customer.id == self.customer.id:
                return goods_receipt
        else:
            return None

    @property
    def url(self):
        if self.weight:
            return url_for("cargo.unload_task", id_=self.id)
        else:
            return url_for("cargo.weigh_unload_task", id_=self.id)

    def delete(self):
        us = self.unload_session
        do_commit(self.model, "delete")
        from litefac.portal.cargo.fsm import fsm
        fsm.reset_obj(us)
        from flask.ext.login import current_user
        from litefac.basemain import timeline_logger

        timeline_logger.info(u"删除了卸货任务%d" % self.id,
                             extra={"obj": self.unload_session.model,
                                    "obj_pk": self.unload_session.id,
                                    "action": u"删除卸货任务",
                                    "actor": current_user})
        fsm.next(constants.cargo.ACT_WEIGHT, current_user)

        from litefac.apis import todo
        # delete todo
        todo.remove_todo(todo.WEIGH_UNLOAD_TASK, self.id)
        return True


class GoodsReceiptWrapper(ModelWrapper):
    def __repr__(self):
        return u"<GoodsReceiptWrapper %d customer-%s>" % (
            self.id, self.customer.name)

    @cached_property
    def unload_task_list(self):
        task_list = []
        for task in self.unload_session.task_list:
            if task.customer.id == self.customer.id:
                task_list.append(task)
        return task_list

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.model, k):
                setattr(self.model, k, v)
        do_commit(self.model)

    @property
    def log_list(self):
        from litefac.apis.log import LogWrapper

        ret = LogWrapper.get_log_list(str(self.id), self.model.__class__.__name__)
        for entry in self.goods_receipt_entries:
            ret.extend(LogWrapper.get_log_list(str(entry.id), "GoodsReceiptEntry"))
        return sorted(ret, lambda a, b: cmp(a.create_time, b.create_time))

    @property
    def stale(self):
        """
        若卸货会话的结束时间晚于收货单的创建时间（即卸货会话在创建收货单之后又打开了），并且的确修改了收货单对应的产品信息，
        我们认为收货单是过时的
        """
        if self.unload_session.finish_time and self.unload_session.finish_time > self.create_time:
            _entries = [(entry.product.id, entry.weight) for entry in
                        self.goods_receipt_entries]
            _uts = [(ut.product.id, ut.weight) for ut in self.unload_task_list]
            return sorted(_entries) != sorted(_uts)
        return False

    def add_product_entries(self):
        for entry in self.goods_receipt_entries:
            do_commit(entry, "delete")
        for ut in self.unload_task_list:
            do_commit(
                models.GoodsReceiptEntry(product=ut.product, weight=ut.weight,
                                         goods_receipt=self.model,
                                         harbor=ut.harbor,
                                         pic_path=ut.pic_path))
        self.model.printed = False
        do_commit(self.model)

    def delete(self):
        do_commit(self.model, "delete")


class GoodsReceiptEntryWrapper(ModelWrapper):
    @property
    def pic_url(self):
        if self.pic_path:
            return url_for("serv_pic", filename=self.pic_path)
        else:
            return ""


def get_unload_session_list(idx=0, cnt=sys.maxint, unfinished_only=False,
                            keywords=None):
    """
    get all the unloading sessions in certain range, ordered by create_time
    descentally
    :param idx: the beginning of the range
    :type idx: int
    :param cnt: the number of unload sessions to get
    :type cnt: int
    :return: the unloading sessions between idx and "idx + cnt" and the
        number of all unload sessions, when there's no sessions, the
        first part will be None
    :rtype: (iterable of UnloadSession|None, total_session_count)
    """
    query = models.UnloadSession.query
    if unfinished_only:
        query = query.filter(models.UnloadSession.finish_time == None)
    if keywords:
        query = query.join(models.UnloadTask).join(models.Customer).filter(
            or_(models.UnloadSession.plate.like("%" + keywords + "%"),
                models.Customer.name.like("%" + keywords + "%")))
    total_cnt = query.count()
    query = query.order_by(
        models.UnloadSession.create_time.desc()).offset(idx).limit(cnt)

    return [UnloadSessionWrapper(us) for us in
            query.all()], total_cnt


def get_unload_session(session_id):
    """
    get unload session from database of given id
    :param session_id:
    :return: unload session of given id if succeed or None
    """
    if not session_id:
        return None
    try:
        return UnloadSessionWrapper(
            models.UnloadSession.query.filter(
                models.UnloadSession.id == session_id).one())
    except NoResultFound:
        return None


def new_unload_session(plate, gross_weight, with_person=False):
    """
    create an unload session
    :return: the newly created unload session
    """
    plate = plate.upper()
    try:
        models.Plate.query.filter(
            models.Plate.name == plate).one()
    except NoResultFound:
        do_commit(models.Plate(name=plate))

    return UnloadSessionWrapper(do_commit(
        models.UnloadSession(plate=plate, gross_weight=gross_weight,
                             with_person=with_person)))


def get_goods_receipts_list(unload_session_id):
    """
    get goods receipt belonging to given unload_session_id from database
    :return: a list of goods receipt
    """
    if not unload_session_id:
        return []
    return [GoodsReceiptWrapper(gr) for gr in
            models.GoodsReceipt.query.filter(
                models.GoodsReceipt.unload_session_id == unload_session_id)
            .all()]


def get_goods_receipt(id_):
    """
    get goods receipt from database
    :return: the goods receipt with given id, or None
    """
    if not id_:
        return None
    try:
        return GoodsReceiptWrapper(models.GoodsReceipt.query.filter(
            models.GoodsReceipt.id == id_).one())
    except NoResultFound:
        return None


def new_goods_receipt(customer_id, unload_session_id):
    """
    create a goods receipt for a customer in database
    :return: the newly created goods receipt
    :raise: ValueError - 若参数发生错误
    """
    import litefac.apis as apis

    customer = apis.customer.get_customer(customer_id)
    if not customer:
        raise ValueError(u"没有该客户(%d)" % int(customer_id))
    unload_session = get_unload_session(unload_session_id)
    if not unload_session:
        raise ValueError(u"没有该卸货会话(%d)" % int(unload_session_id))
    from flask.ext.login import current_user

    model = do_commit(
        models.GoodsReceipt(customer=customer.model, creator=current_user if current_user.is_authenticated() else None,
                            unload_session=unload_session.model))
    gr = GoodsReceiptWrapper(model)
    gr.add_product_entries()
    return gr


def create_or_update_goods_receipt(customer_id, unload_session_id):
    try:
        gr = GoodsReceiptWrapper(models.GoodsReceipt.query.filter(
            models.GoodsReceipt.customer_id == customer_id).filter(
            models.GoodsReceipt.unload_session_id == unload_session_id).one())
        if gr.stale:
            gr.add_product_entries()
        return gr
    except NoResultFound:
        return new_goods_receipt(customer_id, unload_session_id)


def new_unload_task(session_id, harbor, customer_id, creator_id,
                    pic_path, is_last=False):
    """
    持久化创建一个unload task
    :return: 若创建成功，返回创建的unload task
    :rtype: UnloadTaskWrapper
    :raise:
        * ValueError - 如果参数发生错误
    """

    try:
        harbor = models.Harbor.query.filter(models.Harbor.name == harbor).one()
    except NoResultFound:
        raise ValueError(u"没有该装卸点" + harbor)

    try:
        creator = models.User.query.filter(models.User.id == creator_id).one()
    except NoResultFound:
        raise ValueError(_(u"没有该用户(%d)" % int(creator_id)))

    try:
        customer = models.Customer.query.filter(
            models.Customer.id == customer_id).one()
    except NoResultFound:
        raise ValueError(_(u"没有该客户(%d)" % int(customer_id)))

    import litefac.apis as apis

    product = apis.product.get_product(name=constants.DEFAULT_PRODUCT_NAME)
    if not product:
        raise ValueError(_(u"没有该产品" + constants.DEFAULT_PRODUCT_NAME))

    unload_session = get_unload_session(session_id)
    if not unload_session:
        raise ValueError(_(u"没有该卸货会话(%d)" % int(session_id)))

    if unload_session.finish_time:
        raise ValueError(u"该卸货会话(%d)已经结束" % int(session_id))

    ut = do_commit(models.UnloadTask(
        unload_session=unload_session.model,
        harbor=harbor,
        customer=customer,
        creator=creator,
        pic_path=pic_path,
        product=product, is_last=is_last))

    from litefac.apis.todo import new_todo, WEIGH_UNLOAD_TASK
    from litefac.apis.auth import get_user_list

    for to in get_user_list(constants.groups.CARGO_CLERK):
        new_todo(to, WEIGH_UNLOAD_TASK, ut)

    return UnloadTaskWrapper(ut)


def get_unload_task(task_id):
    """
    get unload task by id from database
    :return: the unload task by given id if there do be such task or None
    """
    if not task_id:
        return None
    try:
        return UnloadTaskWrapper(models.UnloadTask.query.filter(
            models.UnloadTask.id == task_id).one())
    except NoResultFound:
        return None


if __name__ == "__main__":
    pass
