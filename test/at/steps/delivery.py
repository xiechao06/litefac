#-*- coding:utf-8 -*-
import json
from flask import g, _request_ctx_stack, session
from pyfeature import step
import yawf

from litefac import models, constants
from litefac.apis.delivery import DeliverySessionWrapper
from litefac.basemain import app, timeline_logger
from litefac.utilities import do_commit
from litefac.test.utils import login, client_login

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

@step(u"收发员创建发货会话")
def _(step, plate, tare):
    return do_commit(models.DeliverySession(plate_=plate, tare=tare))


@step(u"生成StoreBill")
def _(step, customer, harbor, order_type=constants.STANDARD_ORDER_TYPE, weight=5000):
    plate = do_commit(models.Plate(name=generate(5)))
    unload_session = do_commit(models.UnloadSession(plate_=plate, gross_weight=50000))
    product_type = do_commit(models.ProductType(name=generate(5)))
    product = do_commit(models.Product(name=generate(5), product_type=product_type))
    procedure = do_commit(models.Procedure(name=generate(5)))
    goods_receipt = do_commit(models.GoodsReceipt(customer=customer, unload_session=unload_session))
    order = do_commit(models.Order(creator=None, goods_receipt=goods_receipt))
    if order_type == constants.STANDARD_ORDER_TYPE:
        sub_order = do_commit(
            models.SubOrder(harbor=harbor, order=order, product=product, quantity=weight, weight=weight, unit="KG"))
        work_command = do_commit(
            models.WorkCommand(sub_order=sub_order, org_weight=weight, org_cnt=weight, procedure=procedure))
        qir = do_commit(models.QIReport(work_command=work_command, quantity=weight, weight=weight,
                                        result=constants.quality_inspection.FINISHED, actor_id=None))
    else:
        sub_order = models.SubOrder(harbor=harbor, order=order, product=product, quantity=weight/10, weight=weight, unit=u"刀",
                                    order_type=constants.EXTRA_ORDER_TYPE)
        work_command = do_commit(
            models.WorkCommand(sub_order=sub_order, org_weight=weight, org_cnt=weight/10, procedure=procedure))
        qir = do_commit(models.QIReport(work_command=work_command, quantity=weight/10, weight=weight,
                                        result=constants.quality_inspection.FINISHED, actor_id=None))
    return do_commit(models.StoreBill(qir=qir))


@step(u"收发员选择仓单")
def _(step, delivery_session, store_bill_list):
    for store_bill in store_bill_list:
        store_bill.delivery_session = delivery_session
        do_commit(store_bill)


@step(u"装卸工全部装货、完全装货")
def _(step, delivery_session, store_bill):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('l', 'l', c)
            rv = c.post("/delivery_ws/delivery-task?sid=%s&is_finished=1&remain=0&auth_token=%s" % (delivery_session.id, auth_token),
                        data=json.dumps([{"store_bill_id": store_bill.id, "is_finished": 1}]))
            assert 200 == rv.status_code
            delivery_task = models.DeliveryTask.query.filter(
                models.DeliveryTask.delivery_session == delivery_session).order_by(
                models.DeliveryTask.id.desc()).first()
            login('cc', 'cc', c)
            rv = c.post("/delivery/weigh-delivery-task/%d" % delivery_task.id, data={"weight": 6500})
            assert rv.status_code == 302


@step(u"收发员生成发货单")
def _(step, delivery_session):
    with app.test_request_context():
        with app.test_client() as c:
            login('cc', 'cc', c)
            rv = c.post("/delivery/create-consignment-list/%s" % delivery_session.id,
                        data={"customer-pay_mod": json.dumps({customer.id: 0 for customer in
                                                              DeliverySessionWrapper(
                                                                  delivery_session).customer_list})})

            assert 302 == rv.status_code

    return models.Consignment.query.order_by(models.Consignment.id.desc()).first()


@step(u"发货单产品与仓单相同")
def _(step, consignment, store_bill):
    assert len(consignment.product_list) == 1 and consignment.product_list[
        0].product == store_bill.sub_order.product and \
           consignment.product_list[0].weight == store_bill.weight and consignment.product_list[
        0].quantity == store_bill.quantity


@step(u"已关闭的发货会话")
def _(step, plate, tare):
    delivery_session = do_commit(
        models.DeliverySession(plate_=plate, tare=tare, status=constants.delivery.STATUS_CLOSED))
    return delivery_session

@step(u"修改发货会话")
def _(step, delivery_session):
    with app.test_request_context():
        with app.test_client() as c:
            login('cc', 'cc', c)
            rv = c.post("/delivery/delivery-session/%d" % delivery_session.id)
            return rv.status_code

@step(u"重新打开发货会话")
def _(step, delivery_session):
    with app.test_request_context():
        with app.test_client() as c:
            login('cc', 'cc', c)
            rv = c.post("/delivery/delivery-session/%d" % delivery_session.id, data={"__action__": u"打开"})
            assert 302 == rv.status_code


@step(u"可以修改发货会话")
def _(step, delivery_session):
    with app.test_request_context():
        with app.test_client() as c:
            login('cc', 'cc', c)
            rv = c.post("/delivery/delivery-session/%d" % delivery_session.id)
            assert 302 == rv.status_code


@step(u"发货任务$")
def _(step, delivery_session):
    return do_commit(models.DeliveryTask(actor_id=None, delivery_session=delivery_session))


@step(u"修改发货任务")
def _(step, delivery_task):
    with app.test_request_context():
        with app.test_client() as c:
            login('cc', 'cc', c)
            rv = c.post("/delivery/delivery-task/%d" % delivery_task.id)
            return rv.status_code


@step(u"无法修改")
def _(step, status_code):
    assert 403 == status_code


@step(u"修改成功")
def _(step, status_code):
    assert 302 == status_code


@step(u"未打印的发货单")
def _(step, customer, delivery_session, product):
    con = do_commit(models.Consignment(customer=customer, delivery_session=delivery_session, pay_in_cash=True))
    do_commit(models.ConsignmentProduct(consignment=con, delivery_task=delivery_session.delivery_task_list[0],
                                        product=product))
    return con


@step(u"修改发货单的产品")
def _(step, consignment):
    with app.test_request_context():
        with app.test_client() as c:
            login('cc', 'cc', c)
            rv = c.post("/consignment/consignment-product/%d" % consignment.product_list[0].id)
            return rv.status_code
        
@step(u"打印发货单")
def _(step, consignment):
    consignment.MSSQL_ID = 50123
    do_commit(consignment)
    
@step(u"已生成发货单的发货会话")
def _(step,plate,tare, customer, product):
    delivery_session = do_commit(
        models.DeliverySession(plate_=plate, tare=tare, status=constants.delivery.STATUS_CLOSED))
    delivery_task = do_commit(models.DeliveryTask(actor_id=None,delivery_session=delivery_session))
    con = do_commit((models.Consignment(customer=customer, delivery_session=delivery_session, pay_in_cash=True)))
    do_commit(models.ConsignmentProduct(consignment=con, delivery_task=delivery_session.delivery_task_list[0],
                                        product=product))
    return delivery_session

@step(u"新增发货任务")
def _(step, delivery_session, store_bill):
    with app.test_request_context():
        with app.test_client() as c:
            login('cc', 'cc', c)
            rv = c.post("/delivery/store-bill-list/%d" % delivery_session.id, data={"store_bill_list": store_bill.id})
            assert 302 == rv.status_code
            rv = c.post('/auth_ws/login?username=l&password=l')
            assert rv.status_code == 200
            auth_token = json.loads(rv.data)['token']
            rv = c.post("/delivery_ws/delivery-task?sid=%s&is_finished=1&remain=0&auth_token=%s" % (delivery_session.id, auth_token),
                        data=json.dumps([{"store_bill_id": store_bill.id, "is_finished": 1}]))
            assert 200 == rv.status_code

@step(u"提示需要重新生成发货单")
def _(step, delivery_session):
    ds = DeliverySessionWrapper(delivery_session)
    assert ds.stale

@step(u'创建发货任务, 包含两个仓单, 其中一个未完成, 剩余重量超过了原有仓单的重量')
def _(step, delivery_session, store_bill1, store_bill2):
    with app.test_client() as c:
        rv = c.post('/auth_ws/login?username=l&password=l')
        assert rv.status_code == 200
        auth_token = json.loads(rv.data)['token']
        rv = c.post("/delivery_ws/delivery-task?sid=%s&is_finished=1&auth_token=%s&remain=%d" % (delivery_session.id, auth_token, store_bill2.weight+1),
                    data=json.dumps([{"store_bill_id": store_bill1.id, "is_finished": 1}, 
                                     {'store_bill_id': store_bill2.id, 'is_finished': 0}]))
        assert rv.status_code == 201 

@step(u'不能再次创建发货任务，包含两个仓单，全部都完成')
def _(step, delivery_session, store_bill1, store_bill2):
    with app.test_client() as c:
        rv = c.post('/auth_ws/login?username=l&password=l')
        assert rv.status_code == 200
        auth_token = json.loads(rv.data)['token']
        rv = c.post("/delivery_ws/delivery-task?sid=%s&is_finished=1&auth_token=%s" % (delivery_session.id, auth_token),
                    data=json.dumps([{"store_bill_id": store_bill1.id, "is_finished": 1}, 
                                     {'store_bill_id': store_bill2.id, 'is_finished': 1}]))
        print rv.data
        assert rv.status_code == 403 


@step(u'一个异常发货任务申请生成了')
def _(step, codernity_db):
    from litefac.apis.delivery import PermitDeliveryTaskWithAbnormalWeight
    return models.Node.query.filter(models.Node.policy_name=='PermitDeliveryTaskWithAbnormalWeight').one().id


@step(u'批准该申请')
def _(step, node_id):
    with app.test_client() as c:
        login('cc', 'cc', c)
        node = models.Node.query.get(node_id)
        node.approve()
        assert node.approved
        assert node.work_flow.status == yawf.constants.WORK_FLOW_EXECUTED

@step(u'发货任务生成了, 存在一个未发货的仓单, 剩余重量是1001, 另外由两个仓单已经发货完毕, 其重量分别是2000, 1')
def _(step, delivery_session, store_bill_id1, store_bill_id2):
    dt = models.DeliveryTask.query.one()
    assert dt.is_last
    assert dt.delivery_session_id == delivery_session.id 
    store_bill1 = models.StoreBill.query.get(store_bill_id1)
    store_bill2 = models.StoreBill.query.get(store_bill_id2)
    assert store_bill1.delivery_task_id == dt.id
    assert store_bill1.weight == 2000
    assert store_bill2.weight == 1001
    assert store_bill2.delivery_task is None
    new_sb = models.StoreBill.query.filter(models.StoreBill.id!=store_bill_id1).filter(models.StoreBill.id!=store_bill_id2).one()
    assert new_sb.delivery_task_id == dt.id
    assert new_sb.weight == 1
