#-*- coding:utf-8 -*-
from flask import url_for
from . import ModelWrapper
from litefac import models
from litefac.utilities import do_commit
from litefac import database
from .notify import notifications


class TODOWrapper(ModelWrapper):
    @property
    def create_date(self):
        return self.create_time.date()


def new_todo(whom, action, obj=None, msg="", sender=None, **kwargs):
    """
    告诉"whom"对"obj"执行"action" 
    :param whom: who should be responsible for this todo
    :type whom: models.User
    :param unicode action: what should do
    :param obj: action should be performed upon which
    :param msg: supplementary message
    :param sender: who send this message, if not specified, we regard SYSTEM
        send this todo
    :Param kwargs: supplementary information
    """
    todo = do_commit(todo_factory.render(whom, action, obj, msg, sender, **kwargs))
    notify(whom.id, todo.id)


def notify(user_id, to_do_id):
    notifications.add(user_id, to_do_id)


def delete_todo(id_):
    do_commit(models.TODO.query.get(id_), "delete")


def remove_todo(action, obj_pk):
    for to_do in models.TODO.query.filter(models.TODO.action == action).filter(models.TODO.obj_pk == obj_pk).all():
        do_commit(to_do, "delete")


class ToDoFactory(object):
    def __init__(self):
        self.__map = {}

    def render(self, whom, action, obj, msg, sender, **kwargs):
        return self.__map[action](whom, action, obj, msg, sender, **kwargs)

    def upon(self, action):
        def _(strategy):
            self.__map[action] = strategy

        return _


todo_factory = ToDoFactory()


def get_all_notify(user_id):
    id_list = notifications.pop(user_id)
    if id_list:
        return [TODOWrapper(i) for i in models.TODO.query.filter(models.TODO.id.in_(id_list)).all()]
    return []


WEIGH_UNLOAD_TASK = u"weigh_unload_task"
WEIGH_DELIVERY_TASK = u"weigh_delivery_task"
PAY_CONSIGNMENT = u"pay_consignment"
DISPATCH_ORDER = u"dispatch_order"
PERMIT_DELIVERY_TASK_WITH_ABNORMAL_WEIGHT = u'permit_delivery_task_with_abnormal_weight'


@todo_factory.upon(WEIGH_UNLOAD_TASK)
def weigh_unload_task(whom, action, obj, msg, sender, **kwargs):
    """
    称重任务
    """
    from litefac.basemain import data_browser

    msg = u'装卸工%s完成了一次来自%s(车牌号"%s")卸货任务，请称重！' % (obj.creator.username, obj.customer.name, obj.unload_session.plate) + (
    msg and " - " + msg)
    return models.TODO(user=whom, action=action, obj_pk=obj.id, actor=sender,
                       msg=msg,
                       context_url=data_browser.get_form_url(obj.unload_session))


@todo_factory.upon(WEIGH_DELIVERY_TASK)
def weigh_delivery_task(whom, action, obj, msg, sender, **kwargs):
    """
    称重任务
    """
    from litefac.basemain import data_browser

    msg = u'装卸工%s完成了一次来自%s(车牌号"%s")发货任务，请称重！' % (obj.actor.username, obj.customer.name, obj.delivery_session.plate) + (
    msg and " - " + msg)
    return models.TODO(user=whom, action=action, obj_pk=obj.id, actor=sender,
                       msg=msg,
                       context_url=data_browser.get_form_url(obj.delivery_session))


@todo_factory.upon(PAY_CONSIGNMENT)
def pay_consignment(whom, action, obj, msg, sender, **kwargs):
    """
    收款任务
    """
    from litefac.basemain import data_browser

    msg = u'收发员%s创建了一张来自%s(车牌号%s)的发货单，请收款！' % (
        obj.actor.username if obj.actor else "", obj.customer.name, obj.delivery_session.plate) + (msg and " - " + msg)
    return models.TODO(user=whom, action=action, obj_pk=obj.id, actor=sender, msg=msg,
                       context_url=data_browser.get_form_url(obj))


@todo_factory.upon(DISPATCH_ORDER)
def dispatch_order(whom, action, obj, msg, sender, **kwargs):
    """
    下发订单
    """
    from litefac.basemain import data_browser

    msg = u'收发员%s下发了一张编号是%s的订单，请预排产！' % (obj.creator.username if obj.creator else "",
        obj.customer_order_number) + (msg and " - " + msg)
    return models.TODO(user=whom, action=action, obj_pk=obj.id, actor=sender, msg=msg,
                       context_url=data_browser.get_form_url(obj))


@todo_factory.upon(PERMIT_DELIVERY_TASK_WITH_ABNORMAL_WEIGHT)
def permit_delivery_task_with_abnormal_weight(whom, action, obj, msg, sender, **kwargs):
    doc = database.codernity_db.get('id', obj.tag, with_doc=True)
    loader = models.User.query.get(doc['loader_id'])
    msg = u'装卸工%s完成了剩余重量异常的发货任务，请处理!' % loader.username 
    return models.TODO(user=whom, action=action, obj_pk=obj.id, actor=sender, msg=msg,
                       context_url=url_for('work_flow.node_list'))

