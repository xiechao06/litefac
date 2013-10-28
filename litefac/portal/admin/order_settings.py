# -*- coding: utf-8 -*-

from flask.ext.admin.contrib.sqlamodel import ModelView

import flask.ext.admin
from litefac.permissions import AdminPermission

class OrderModelView(ModelView):
    def is_accessible(self):
        return AdminPermission.can()

    #can_create = False
    #can_edit = False
    #can_delete = False

    column_list = ["id", "customer_order_number", "creator", "finish_time", "customer", 'dispatched', "sub_order_list"]
    list_select_related = ("sub_order_list", )

    list_formatters = {"sub_order_list": lambda context, model, name: ", ".join([str(sb.id) for sb in model.sub_order_list])}

class SubOrderModelView(ModelView):
    can_create = False
    can_delete = False

    from wtforms import TextField
    form_overrides = {"customer": TextField}
    form_args = {"customer": {"label": "你好", "xya": "aaaa"}}

    column_labels = {"order": u"订单", "product": u"产品"}
    column_list = ["id", "order", "customer", "product"]
    list_formatters = {"order": lambda context, model, name: model.order.customer_order_number, "product": lambda context, model, name: model.product.name, 
                       "customer": lambda context, model, name: model.order.goods_receipt.customer.name, "harbor": lambda context, model, name: model.harbor.name}
    form_columns = ("weight", )

    def is_accessible(self):
        return AdminPermission.can()
