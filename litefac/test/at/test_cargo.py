
# -*- coding: UTF-8 -*-
from hashlib import md5

from pyfeature import Feature, Scenario, given, and_, when, then, clear_hooks
import litefac
from litefac.basemain import app
from litefac.database import db

def test_cargo():
    from pyfeature import flask_sqlalchemy_setup

    flask_sqlalchemy_setup(app, db, create_step_prefix=u"创建",
                           model_name_getter=lambda model: model.__name__,
                           attr_name_getter=lambda model, attr: model.__col_desc__.get(attr, attr),
                           set_step_pattern=u'(\w+)([\.\w+]+)设置为(.+)')

    with Feature(u"卸货会话生成收货单", ['litefac.test.at.steps.cargo'], verbose=False):
        with Scenario(u"准备数据"):
            plate = given(u"创建Plate(浙B 11112)")
            harbor = and_(u"创建Harbor(foo车间)")
            customer = and_(u"创建Customer(宁波机床厂)", abbr="aaa")
            customer2 = and_(u"创建Customer(宁力紧固件)", abbr="bbb")
            dpt = and_(u"创建ProductType(默认加工件)")
            and_(u"创建Product(默认加工件)", product_type=dpt)
            product_type = and_(u"创建ProductType(foo)")
            product = and_(u"创建Product(foo)", product_type=product_type)
            cargo_clerk_group = and_(u'创建Group(cargo_clerk)', id=litefac.constants.groups.CARGO_CLERK, 
                                     default_url='/cargo/unload-session-list')
            and_(u"创建User", username="cc", password=md5("cc").hexdigest(), groups=[cargo_clerk_group])
            loader_group = and_(u'创建Group(loader)', id=litefac.constants.groups.LOADER)
            and_(u'创建User', username="l", password=md5("l").hexdigest(), groups=[loader_group])

        with Scenario(u"最简完整流程"):
            us = when(u'收发员创建UnloadSession， 毛重是10000公斤', plate)
            ut = and_(u'装卸工进行卸货，该货物来自宁波机床厂', customer, harbor, product, us, is_last=True)
            and_(u'收发员称重8000公斤', ut)

            then(u"卸货任务的重量是2000公斤", ut)
            and_(u'卸货会话已经关闭', us)

            gr_list = when(u'收发员生成收货单', us)
            then(u'该收货单中包含一个项目，该项目的客户是宁波机床厂, 项目的重量是2000公斤', gr_list)

        with Scenario(u"包含多次卸货任务的卸货会话"):
            us = when(u'收发员创建UnloadSession， 毛重是10000公斤', plate)
            ut1 = and_(u'装卸工进行卸货，该货物来自宁波机床厂', customer, harbor, product, us, is_last=False)
            then(u'装卸工此时不能进行卸货', us)

            when(u'收发员称重8000公斤', ut1)
            then(u"卸货任务的重量是2000公斤", ut1)
            and_(u'卸货会话没有关闭', us)

            ut2 = when(u'装卸工进行卸货，该货物来自宁力紧固件', customer2, harbor, product, us, is_last=True)
            and_(u'收发员称重5000公斤', ut2)
            then(u'卸货任务的重量是3000公斤', ut2)
            and_(u"卸货会话已经关闭", us)

            gr_list = when(u'收发员生成收货单', us)
            then(u'该会话中包含两个项目', gr_list)
            and_(u'项目的客户是宁波机床厂, 项目的重量是2000公斤', gr_list[0])
            and_(u'项目的客户是宁力紧固件, 项目的重量是3000公斤', gr_list[1])

        with Scenario(u'除非卸货会话关闭，否则卸货会话都可以修改'):
            us = when(u'收发员创建卸货会话, 其状态是待称重')
            ut = and_(u'装卸工创建卸货任务', customer, harbor, product, us)
            and_(u'修改卸货会话的车牌号为浙B 00002', us)
            and_(u'修改卸货会话的毛重为10000公斤', us)
            then(u'卸货会话的车牌号为浙B 00002', us)
            and_(u'卸货会话的重量为10000公斤', us)
            and_(u'修改卸货任务的重量为2000公斤', ut)
            then(u'卸货任务的重量是2000公斤', ut)

            when(u'关闭卸货会话',us)
            then(u'不能修改卸货会话',us)
            and_(u'不能修改卸货任务',ut)

        with Scenario(u'收发员删除卸货任务'):
            us = given(u"未关闭的卸货会话")
            ut1 = and_(u"已称重的卸货任务", us, customer, harbor, product)
            ut2 = and_(u"未称重的卸货任务", us, customer, harbor, product)
            rv = when(u"删除卸货任务", ut1)
            then(u"无法删除", rv)
            rv = when(u"删除卸货任务", ut2)
            then(u"删除成功", rv)

        with Scenario(u'收发员强行关闭卸货会话'):
            us = given(u"未称重未关闭的卸货会话", customer, harbor, product)
            rv = when(u"收发员关闭卸货会话", us)
            then(u"关闭失败", rv)
            when(u"收发员称重卸货会话", us)
            rv = and_(u"收发员关闭卸货会话", us)
            then(u"关闭成功", rv)

        with Scenario(u'收发员创建卸货会话时，不能选择正在装货或者卸货的车辆'):
            plate_a = given(u"正在装货的车辆", plate_name="Ijkdplate_a")
            plate_list = when(u"收发员创建新卸货会话")
            then(u"车辆列表中无上述车辆", plate_a, plate_list)

        with Scenario(u'收发员打开关闭的卸货会话，并且修改'):
            us = given(u"卸货会话已关闭，未生成收货单", customer, harbor,plate, product)
            when(u"收发员重新打开卸货会话", us)
            then(u"收发员修改其卸货任务的重量为5000KG", us)
            and_(u"收发员关闭卸货会话", us)
            gr = then(u"生成收货单。其产品重量为5000KG", us)
            when(u"收发员重新打开卸货会话", us)
            and_(u"收发员修改其卸货任务的重量为6000KG", us)
            then(u"收货单未过时", gr)
            when(u"又新增一卸货任务", us)
            then(u"收货单过时", gr)

        with Scenario(u'若收货单过时，或者已经生成了订单，那么不能修改收货单'):
            us = given(u"卸货会话已关闭，未生成收货单", customer, harbor,plate, product)
            gr_list = and_(u'收发员生成收货单', us)
            when(u"收发员重新打开卸货会话", us)
            and_(u'又新增一卸货任务',us)
            then(u'收货单过时', gr_list[0])
            and_(u'不能修改收货单', gr_list[0])

            gr_list = when(u'重新生成收货单', us)
            and_(u'生成订单',gr_list[0])
            then(u'不能修改收货单',gr_list[0])
    
    clear_hooks()

if __name__ == "__main__":
    test_cargo()
