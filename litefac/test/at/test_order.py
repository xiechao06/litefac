#-*- coding:utf-8 -*-
from litefac import constants
from pyfeature import Feature, Scenario, given, when, and_, then, flask_sqlalchemy_setup, clear_hooks

from litefac.basemain import app
from litefac.database import db


def generate(times=1):
    from random import choice
    import string

    temp = ""
    for i in range(times):
        temp += choice(string.letters)
    return temp


def test():
    flask_sqlalchemy_setup(app, db, create_step_prefix=u"创建",
                           model_name_getter=lambda model: model.__name__,
                           attr_name_getter=lambda model, attr: model.__col_desc__.get(attr, attr),
                           set_step_pattern=u'(\w+)([\.\w+]+)设置为(.+)')

    with Feature(u"订单测试",step_files=["litefac.test.at.steps.order"]):
        with Scenario(u"准备数据"):
            plate = given(u"创建Plate", name=generate(5))
            product_type_default = and_(u"创建ProductType", name=constants.DEFAULT_PRODUCT_TYPE_NAME)
            product_default = and_(u"创建Product", name=constants.DEFAULT_PRODUCT_NAME,
                                   product_type=product_type_default)
            group = and_(u'创建Group(cargo_clerk)', name='cargo_clerk', default_url='/cargo/unload-session-list')
            and_(u"创建User", username="cc", password="cc", groups=[group])
            customer = and_(u"创建Customer", name=generate(5), abbr=generate(2))
            department = and_(u"创建Department", name=generate(5))
            harbor = and_(u"创建Harbor", name=generate(5), department=department)

        with Scenario(u"最简单流程"):
            gr = given(u"收货单", customer, harbor)
            order = and_(u"生成订单", gr, order_type=constants.STANDARD_ORDER_TYPE)
            when(u"完善订单", order)
            status_code = and_(u"下发订单", order)
            then(u"操作成功", status_code)

if __name__ == '__main__':
    test()

