#-*- coding:utf-8 -*-
from . import Widget, DASHBOARD_WIDGETS
from sqlalchemy import func

from litefac import models, constants
from litefac.database import db
from litefac.permissions.roles import AdminPermission


class ManufactureWidget(Widget):
    def query(self):
        return db.session.query(func.sum(models.WorkCommand.org_weight).label(u"生成中重量")).filter(
            models.WorkCommand.status != constants.work_command.STATUS_FINISHED)

    @property
    def data(self):
        return int(self.query().first()[0])

    def try_view(self):
        AdminPermission.test()

manufacture_widget = ManufactureWidget(name=u"生产中重量", description=u"生成中工单的总重量")


class ToDeliveryWidget(Widget):
    def query(self):
        return db.session.query(func.sum(models.StoreBill.weight).label(u"待发货重量")).filter(models.StoreBill.delivery_task_id == None)

    @property
    def data(self):
        return int(self.query().first()[0])

    def try_view(self):
        AdminPermission.test()

to_delivery_widget = ToDeliveryWidget(name=u"待发货重量", description=u"待发货的仓单的总重量")
DASHBOARD_WIDGETS.append(manufacture_widget)
DASHBOARD_WIDGETS.append(to_delivery_widget)