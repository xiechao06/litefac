#-*- coding:utf-8 -*-
import numbers
from datetime import datetime, timedelta
from flask import request
from . import time_line_page
from litefac.utilities.decorators import templated, nav_bar_set
from litefac.apis import wraps
from litefac.models import Log
from litefac import models

from flask.ext.databrowser import ModelView
from flask.ext.databrowser.filters import EqualTo, Between
from flask.ext.login import current_user
from flask.ext.principal import PermissionDenied

from flask.ext.databrowser import filters


class ObjClsFilter(filters.BaseFilter):
    UNLOAD_SESSION = 1
    GOODS_RECEIPT = 2
    ORDER = 3
    WORK_COMMAND = 4

    def set_sa_criterion(self, query):
        if isinstance(self.value, numbers.Number) or self.value.isdigit():
            self.value = int(self.value)
        obj_cls = ""
        if self.value == self.UNLOAD_SESSION:
            obj_cls = "UnloadSession"
        elif self.value == self.GOODS_RECEIPT:
            obj_cls = "GoodsReceipt"
        elif self.value == self.ORDER:
            obj_cls = "Order"
        elif self.value == self.WORK_COMMAND:
            obj_cls = "WorkCommand"
        if obj_cls:
            query = query.filter(Log.obj_cls == obj_cls)
        return query


class MyBetween(Between):
    format = "%Y-%m-%d"

    @property
    def input_type(self):
        return "date", "date"


my_between = MyBetween("create_time", u"从", sep=u"到",
                       default_value=[datetime.now().strftime(MyBetween.format),
                                      (datetime.now() + timedelta(days=7)).strftime(MyBetween.format)])

obj_cls_fltr = ObjClsFilter("obj_class", name=u"是", hidden=True,
                            options=[(ObjClsFilter.UNLOAD_SESSION, u"卸货会话"),
                                     (ObjClsFilter.GOODS_RECEIPT, u"收货会话"),
                                     (ObjClsFilter.ORDER, u"订单"),
                                     (ObjClsFilter.WORK_COMMAND, u"工单")])


class TimeLineModelView(ModelView):
    def scaffold_list(self, objs):
        return [wraps(obj) for obj in objs]

    list_template = "timeline/timeline.html"

    __column_labels__ = {"actor": u"操作员", "create_time": u"创建时间"}

    def try_view(self, processed_obj=None):
        if current_user.is_anonymous():
            raise PermissionDenied

    def get_column_filters(self):
        return [EqualTo("actor", u"是", default_value=current_user.id),
                my_between, obj_cls_fltr]


time_line_model_view = TimeLineModelView(Log, u"日志")
