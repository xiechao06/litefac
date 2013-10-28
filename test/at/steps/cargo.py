# -*- coding: UTF-8 -*-
"""
这里是test_cargo.py 的具体实现。
"""
from datetime import datetime
from flask import g, _request_ctx_stack, session
from pyfeature import *

from litefac import models
from litefac.basemain import app, timeline_logger
from litefac.database import db
from litefac.utilities import do_commit

from litefac.test.utils import client_login

#patch logger
timeline_logger.handlers = []
app.config["CSRF_ENABLED"] = False
app.config["WTF_CSRF_ENABLED"] = False


def refresh(obj):
    return db.session.query(obj.__class__).filter(obj.__class__.id == obj.id).one()


@step(u"收发员创建UnloadSession， 毛重是(\d+)公斤")
def _(step, weight, plate_):
    return do_commit(models.UnloadSession(plate_=plate_, gross_weight=weight))


@step(u"装卸工进行卸货，该货物来自(.+)")
def _(step, customer_name, customer, harbor, product, us, is_last):
    from litefac.constants.cargo import STATUS_WEIGHING

    us.status = STATUS_WEIGHING
    return do_commit(models.UnloadTask(customer=customer, unload_session=us, harbor=harbor, creator=None, pic_path="",
                                       product=product, is_last=is_last))


@app.before_request
def patch():
    """
    needn't login in
    """
    g.identity.can = lambda p: True
    from litefac.apis.auth import UserWrapper

    user = UserWrapper(models.User.query.first())
    session['current_group_id'] = user.groups[0].id
    _request_ctx_stack.top.user = user


@step(u"收发员称重(\d+)公斤")
def _(step, weight, unload_task):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/weigh-unload-task/%d" % unload_task.id,
                        data={"weight": weight, "product_type": 1, "product": 1, "customer": unload_task.customer.id})
            assert 302 == rv.status_code


@step(u"卸货会话已经关闭")
def _(step, us):
    us = refresh(us)
    from litefac.constants.cargo import STATUS_CLOSED

    assert STATUS_CLOSED == us.status


@step(u"收发员生成收货单")
def _(step, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/unload-session/%d" % us.id, data={"__action__": u"生成收货单"})
            assert 302 == rv.status_code
            return db.session.query(models.GoodsReceipt).filter(models.GoodsReceipt.unload_session_id == us.id).all()


@step(u"该收货单中包含一个项目，该项目的客户是(.+), 项目的重量是(\d+)公斤")
def _(step, customer_name, weight, gr_list):
    assert 1 == len(gr_list)
    assert customer_name == gr_list[0].customer.name
    assert int(weight) == sum(entry.weight for entry in gr_list[0].goods_receipt_entries)


@step(u"装卸工此时不能进行卸货")
def _(step, us):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('l', 'l', c)
            rv = c.get("/cargo_ws/unload-session-list?auth_token=" + auth_token)
            from flask import json

            assert not [i for i in json.loads(rv.data)["data"] if not i["isLocked"]]


@step(u"卸货会话没有关闭")
def _(step, us):
    us = refresh(us)
    from litefac.constants.cargo import STATUS_CLOSED

    assert STATUS_CLOSED != us.status


@step(u"该会话中包含两个项目")
def _(step, gr_list):
    assert 2 == len(gr_list)


@step(u"项目的客户是(.+), 项目的重量是(\d+)公斤")
def _(step, customer_name, weight, gr):
    assert customer_name == gr.customer.name
    assert int(weight) == sum(entry.weight for entry in gr.goods_receipt_entries)


@step(u"收发员创建卸货会话, 其状态是待称重")
def _(step):
    plate_ = do_commit(models.Plate(name=u"浙F oofoo"))
    return do_commit(models.UnloadSession(plate_=plate_, gross_weight=1000))


@step(u"装卸工创建卸货任务")
def _(step, customer, harbor, product, us):
    from litefac.constants.cargo import STATUS_WEIGHING, STATUS_LOADING

    us.status = STATUS_WEIGHING
    ut = do_commit(models.UnloadTask(customer=customer, unload_session=us, harbor=harbor, creator=None, pic_path="",
                                     product=product, is_last=False))
    us.status = STATUS_LOADING
    return ut


@step(u"修改卸货会话的车牌号为(.+)")
def _(step, plate_name, us):
    plate_ = do_commit(models.Plate(name=plate_name))
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post(u"/cargo/unload-session/%d" % us.id, data={"plate_": plate_name})
            assert 302 == rv.status_code


@step(u"修改卸货会话的毛重为(\d+)公斤")
def _(step, weight, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post(u"/cargo/unload-session/%d" % us.id, data={"gross_weight": int(weight)})
            assert 302 == rv.status_code


@step(u"卸货会话的车牌号为浙B 00002")
def _(step, us):
    us = refresh(us)
    assert u"浙B 00002" == us.plate


@step(u"卸货会话的重量为(\d+)公斤")
def _(step, weight, us):
    us = refresh(us)
    assert int(weight) == us.gross_weight


@step(u"修改卸货任务的重量为(\d+)公斤")
def _(step, weight, ut):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post(u"/cargo/unload-task/%d" % ut.id, data={"weight": weight})
            assert 302 == rv.status_code


@step(u"卸货任务的重量是(\d+)公斤")
def _(step, weight, ut):
    ut = refresh(ut)
    assert int(weight) == ut.weight


@step(u"关闭卸货会话")
def _(step, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/unload-session/%d" % us.id, data={"__action__": u"关闭"})
            assert 302 == rv.status_code


@step(u"不能修改卸货会话")
def _(step, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post(u"/cargo/unload-session/%d" % us.id, data={"gross_weight": 123123})
            assert 403 == rv.status_code


@step(u"不能修改卸货任务")
def _(step, ut):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post(u"/cargo/unload-task/%d" % ut.id, data={"weight": 12312})
            assert 403 == rv.status_code


@step(u"未关闭的卸货会话")
def _(step):
    from random import choice
    import string

    plate_ = do_commit(models.Plate(name=u"浙%s %s%s%s%s%s" % (
        choice(string.ascii_lowercase), choice(string.ascii_lowercase), choice(string.ascii_lowercase),
        choice(string.ascii_lowercase), choice(string.ascii_lowercase), choice(string.ascii_lowercase))))
    return do_commit(models.UnloadSession(plate_=plate_, gross_weight=1000))


@step(u"已称重的卸货任务")
def _(step, us, customer, harbor, product):
    from litefac.constants.cargo import STATUS_WEIGHING, STATUS_LOADING

    us.status = STATUS_WEIGHING
    ut = do_commit(models.UnloadTask(customer=customer, unload_session=us, harbor=harbor, creator=None, pic_path="",
                                     product=product, is_last=False, weight=5000))
    us.status = STATUS_LOADING
    return ut


@step(u"未称重的卸货任务")
def _(step, us, customer, harbor, product):
    from litefac.constants.cargo import STATUS_WEIGHING

    ut = do_commit(models.UnloadTask(customer=customer, unload_session=us, harbor=harbor, creator=None, pic_path="",
                                     product=product, is_last=False))
    us.status = STATUS_WEIGHING
    return ut


@step(u"删除卸货任务")
def _(step, ut):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/ajax/unload-task/%d" % ut.id, data={"action": u"delete"})
            return rv.status_code


@step(u"无法删除")
def _(step, status_code):
    assert 403 == status_code


@step(u"删除成功")
def _(step, status_code):
    assert 200 == status_code


@step(u"未称重未关闭的卸货会话")
def _(step, customer, harbor, product):
    from random import choice
    import string

    plate_ = do_commit(models.Plate(name=u"浙%s %s%s%s%s%s" % (
        choice(string.ascii_lowercase), choice(string.ascii_lowercase), choice(string.ascii_lowercase),
        choice(string.ascii_lowercase), choice(string.ascii_lowercase), choice(string.ascii_lowercase))))
    us = do_commit(models.UnloadSession(plate_=plate_, gross_weight=100000))
    from litefac.constants.cargo import STATUS_WEIGHING

    ut = do_commit(models.UnloadTask(customer=customer, unload_session=us, harbor=harbor, creator=None, pic_path="",
                                     product=product, is_last=False))
    us.status = STATUS_WEIGHING
    return us


@step(u"收发员关闭卸货会话")
def _(step, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/unload-session/%d" % us.id, data={"__action__": u"关闭"})
            return rv.status_code


@step(u"关闭失败")
def _(step, status_code):
    assert 403 == status_code


@step(u"收发员称重卸货会话")
def _(step, us):
    us = refresh(us)
    for ut in us.task_list:
        ut.weight = 4000
    from litefac.constants.cargo import STATUS_LOADING

    us.status = STATUS_LOADING
    do_commit(us)


@step(u"关闭成功")
def _(step, status_code):
    assert 302 == status_code


@step(u"正在装货的车辆")
def _(step, plate_name):
    plate_ = do_commit(models.Plate(name=plate_name))
    do_commit(models.UnloadSession(plate_=plate_, gross_weight=123))
    return plate_


@step(u"收发员创建新卸货会话")
def _(step):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.get("/cargo/unload-session")
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(rv.data)
            return [i["value"] for i in soup.find_all("option")]


@step(u"车辆列表中无上述车辆")
def _(step, plate, plate_list):
    assert plate.name not in plate_list


@step(u"卸货会话已关闭，未生成收货单")
def _(step, customer, harbor, plate, product):
    us = do_commit(models.UnloadSession(plate_=plate, gross_weight=123123123))
    from litefac.constants.cargo import STATUS_CLOSED

    us.status = STATUS_CLOSED
    import datetime

    us.finish_time = datetime.datetime.now()
    do_commit(us)
    ut = do_commit(models.UnloadTask(customer=customer, unload_session=us, harbor=harbor, creator=None, pic_path="",
                                     product=product, is_last=False))
    return us


@step(u"收发员重新打开卸货会话")
def _(step, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/unload-session/%d" % us.id, data={"__action__": u"打开"})
            assert 302 == rv.status_code


@step(u"收发员修改其卸货任务的重量为(\d+)KG")
def _(step, weight, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/unload-task/%d" % us.task_list[0].id, data={"weight": weight})
            assert 302 == rv.status_code


@step(u"生成收货单。其产品重量为(\d+)KG")
def _(step, weight, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/unload-session/%d" % us.id, data={"__action__": u"生成收货单"})
            assert 302 == rv.status_code
            gr = models.GoodsReceipt.query.order_by(models.GoodsReceipt.id.desc()).first()
            assert int(weight) == sum(i.weight for i in gr.goods_receipt_entries)
            return gr


@step(u"收货单未过时")
def _(step, gr):
    from litefac.apis import wraps

    assert not wraps(gr).stale


@step(u"又新增一卸货任务")
def _(step, us):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('l', 'l', c)
            rv = c.post(
                u"/cargo_ws/unload-task?actor_id=1&customer_id=1&harbour=foo车间&is_finished=1&session_id=%d"
                u"&auth_token=%s" % (
                us.id, auth_token))
            assert 200 == rv.status_code
            rv = c.post("/cargo/weigh-unload-task/%s" % rv.data,
                        data={"weight": 2213, "product_type": 1, "product": 1, "customer": 1})
            assert 302 == rv.status_code


@step(u"收货单过时")
def _(step, gr):
    from litefac.apis import wraps

    assert wraps(gr).stale


@step(u"不能修改收货单")
def _(step, gr):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/goods_receipt/goods-receipt/%d" % gr.id)
            assert 403 == rv.status_code


@step(u"重新生成收货单")
def _(step, us):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/cargo/unload-session/%d" % us.id, data={"__action__": u"生成收货单"})
            assert 302 == rv.status_code
            return models.GoodsReceipt.query.filter(models.GoodsReceipt.unload_session_id == us.id).all()


@step(u"生成订单")
def _(step, gr):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/goods_receipt/goods-receipt/%d" % gr.id, data={"__action__": u"生成计重类型订单"})
            assert 302 == rv.status_code
