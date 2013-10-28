#-*- coding:utf-8 -*-
from flask import g, _request_ctx_stack, session
from pyfeature import step

from litefac import models, constants
from litefac.basemain import timeline_logger, app
from litefac.utilities import do_commit

timeline_logger.handlers = []

app.config["CSRF_ENABLED"] = False
app.config["WTF_CSRF_ENABLED"] = False

def generate(times=1):
    from random import choice
    import string

    temp = ""
    for i in range(times):
        temp += choice(string.letters)
    return temp

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


@step(u"收货单")
def _(step, customer, harbor):
    plate = do_commit(models.Plate(name=generate(5)))
    unload_session = do_commit(models.UnloadSession(plate_=plate, gross_weight=50000))
    product_type = do_commit(models.ProductType(name=generate(5)))
    product = do_commit(models.Product(name=generate(5), product_type=product_type))
    procedure = do_commit(models.Procedure(name=generate(5)))
    goods_receipt = do_commit(models.GoodsReceipt(customer=customer, unload_session=unload_session))
    for i in xrange(3):
        goods_receipt_entry = do_commit(
            models.GoodsReceiptEntry(goods_receipt=goods_receipt, product=product, weight=5000, harbor=harbor))
    return goods_receipt


@step(u"生成订单")
def _(step, goods_receipt, order_type):
    if order_type == constants.STANDARD_ORDER_TYPE:
        action = u"生成计重类型订单"
    else:
        action = u"生成计件类型订单"
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/goods_receipt/goods-receipt/%d" % goods_receipt.id, data={"__action__": action})
            assert 302 == rv.status_code
            return models.Order.query.order_by(models.Order.id.desc()).first()


@step(u"完善订单")
def _(step, order):
    for count, sub_order in enumerate(order.sub_order_list):
        with app.test_request_context():
            with app.test_client() as c:
                rv = c.post("/order/sub-order/%d" % sub_order.id, data={"due_time": "2013-08-09"})
                assert 302 == rv.status_code
                if count == len(order.sub_order_list) - 1:
                    rv = c.post("/order/order/%d" % order.id, data={"__action__": u"标记为完善"})
                    assert 302 == rv.status_code


@step(u"下发订单")
def _(step, order):
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post("/order/order/%s" % order.id, data={"__action__": u"下发"})
            return rv.status_code

@step(u"操作成功")
def _(step, status_code):
    assert 302 == status_code

