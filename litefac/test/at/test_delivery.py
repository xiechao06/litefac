#-*- coding:utf-8 -*-
from tempfile import mkdtemp
from hashlib import md5
import shutil

from pyfeature import (Feature, Scenario, given, when, and_, then, 
                       flask_sqlalchemy_setup, clear_hooks, before_each_feature, after_each_feature)
import mock
import yawf

import litefac
from litefac import constants

from litefac.basemain import app
from litefac.database import db, codernity_db

from CodernityDB.database import Database

def generate(times=1):
    from random import choice
    import string

    temp = ""
    for i in range(times):
        temp += choice(string.letters)
    return temp

patcher = None

def test():
    
    @before_each_feature
    def setup(feature):
        app.config['CODERNITY_DATABASE_PATH'] = mkdtemp()
        global patcher
        patcher = mock.patch.dict(litefac.database.__dict__, 
                                  {
                                      "codernity_db": Database(app.config['CODERNITY_DATABASE_PATH'])
                                  })
        patcher.start()
        litefac.database.codernity_db.create()
        

    @after_each_feature
    def teardown(feature):
        litefac.database.codernity_db.close()
        shutil.rmtree(app.config['CODERNITY_DATABASE_PATH'])
        patcher.stop()

    flask_sqlalchemy_setup(app, db, create_step_prefix=u"创建",
                           model_name_getter=lambda model: model.__name__,
                           attr_name_getter=lambda model, attr: model.__col_desc__.get(attr, attr),
                           set_step_pattern=u'(\w+)([\.\w+]+)设置为(.+)')

    with Feature(u"发货会话测试", step_files=["litefac.test.at.steps.delivery"]):
        with Scenario(u"准备数据"):
            plate = given(u"创建Plate", name=generate(5))
            product_type_default = and_(u"创建ProductType", name=constants.DEFAULT_PRODUCT_TYPE_NAME)
            product_default = and_(u"创建Product", name=constants.DEFAULT_PRODUCT_NAME,
                                   product_type=product_type_default)
            group_cc = and_(u'创建Group(cargo_clerk)', name='cargo_clerk', 
                            id=constants.groups.CARGO_CLERK, default_url='/cargo/unload-session-list')
            and_(u"创建User", username="cc", password=md5("cc").hexdigest(), groups=[group_cc])
            group_loader = and_(u'创建Group(loader)', name='loader', id=constants.groups.LOADER)
            and_(u"创建User", username="l", password=md5("l").hexdigest(), groups=[group_loader])
            customer = and_(u"创建Customer", name=generate(5), abbr=generate(2))
            department = and_(u"创建Department", name=generate(5))
            harbor = and_(u"创建Harbor", name=generate(5), department=department)
            store_bill1 = and_(u"生成StoreBill", customer, harbor=harbor)
            store_bill2 = and_(u"生成StoreBill", customer, harbor=harbor)

        with Scenario(u"创建发货会话，并生成发货单"):
            delivery_session = when(u"收发员创建发货会话", plate=plate, tare=1500)
            then(u"收发员选择仓单", delivery_session, [store_bill1, store_bill2])
            and_(u"装卸工全部装货、完全装货", delivery_session, store_bill1)
            consignment = and_(u"收发员生成发货单", delivery_session)
            then(u"发货单产品与仓单相同", consignment, store_bill1)

        with Scenario(u"修改发货会话"):
            delivery_session = given(u"已关闭的发货会话", plate, tare=1000)
            status_code = when(u"修改发货会话", delivery_session)
            then(u"无法修改", status_code)
            when(u"重新打开发货会话", delivery_session)
            status_code = and_(u"修改发货会话", delivery_session)
            then(u"修改成功", status_code)

        with Scenario(u"修改发货任务"):
            delivery_session = given(u"已关闭的发货会话", plate, tare=1000)
            delivery_task = and_(u"发货任务", delivery_session)
            status_code = when(u"修改发货任务", delivery_task)
            then(u"无法修改", status_code)
            when(u"重新打开发货会话", delivery_session)
            status_code = and_(u"修改发货任务", delivery_task)
            then(u"修改成功", status_code)

        with Scenario(u"修改发货单"):
            consignment = given(u"未打印的发货单", customer, delivery_session, store_bill1.sub_order.product)
            status_code = when(u"修改发货单的产品", consignment)
            then(u"修改成功", status_code)
            when(u"打印发货单", consignment)
            status_code = and_(u"修改发货单的产品", consignment)
            then(u"无法修改", status_code)

        with Scenario(u"对已生成发货单的发货会话，新增发货任务"):
            delivery_session = given(u"已生成发货单的发货会话", plate, 1000, customer, store_bill1.sub_order.product)
            then(u"重新打开发货会话", delivery_session)
            when(u"新增发货任务", delivery_session, store_bill2)
            then(u"提示需要重新生成发货单", delivery_session)
        
    with Feature(u"剩余重量异常", step_files=["litefac.test.at.steps.delivery"]):
        with Scenario(u'数据准备'):
            plate = given(u"创建Plate", name=generate(5))
            product_type_default = and_(u"创建ProductType", name=constants.DEFAULT_PRODUCT_TYPE_NAME)
            product_default = and_(u"创建Product", name=constants.DEFAULT_PRODUCT_NAME,
                                   product_type=product_type_default)
            group_cc = and_(u'创建Group(cargo_clerk)', name='cargo_clerk', 
                            id=constants.groups.CARGO_CLERK, default_url='/cargo/unload-session-list')
            and_(u"创建User", username="cc", password=md5("cc").hexdigest(), groups=[group_cc])
            group_loader = and_(u'创建Group(loader)', name='loader', id=constants.groups.LOADER)
            and_(u"创建User", username="l", password=md5("l").hexdigest(), groups=[group_loader])
            customer = and_(u"创建Customer", name=generate(5), abbr=generate(2))
            department = and_(u"创建Department", name=generate(5))
            harbor = and_(u"创建Harbor", name=generate(5), department=department)
            store_bill1 = and_(u"生成StoreBill", customer, harbor=harbor, weight=2000)
            store_bill2 = and_(u"生成StoreBill", customer, harbor=harbor, weight=1000)
            
        with Scenario(u'最简情况'):
            delivery_session = when(u"收发员创建发货会话", plate=plate, tare=1500)
            then(u"收发员选择仓单", delivery_session, [store_bill1, store_bill2])
            and_(u'创建发货任务, 包含两个仓单, 其中一个未完成, 剩余重量超过了原有仓单的重量', delivery_session, store_bill1, store_bill2)
            node_id = then(u'一个异常发货任务申请生成了', yawf.WorkFlowEngine.instance.db)
            then(u'不能再次创建发货任务，包含两个仓单，全部都完成', delivery_session, store_bill1, store_bill2)
            when(u'批准该申请', node_id)
            then(u'发货任务生成了, 存在一个未发货的仓单, 剩余重量是1001, 另外由两个仓单已经发货完毕, 其重量分别是2000, 1', delivery_session, store_bill1.id, store_bill2.id)

    clear_hooks()

if __name__ == '__main__':
    test()
