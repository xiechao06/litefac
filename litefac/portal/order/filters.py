# -*- coding: utf-8 -*-

import numbers
from sqlalchemy import or_
from flask.ext.databrowser import filters
from litefac.models import Order, WorkCommand, SubOrder
from litefac import constants

class CategoryFilter(filters.BaseFilter):
    
    UNDISPATCHED_ONLY = 1
    DELIVERABLE_ONLY = 2
    ACCOUNTABLE_ONLY = 3

    def set_sa_criterion(self, query):
        from litefac import models
        from sqlalchemy import and_
        from litefac import constants
        if isinstance(self.value, numbers.Number) or self.value.isdigit():
            self.value = int(self.value)
            if self.value == self.ACCOUNTABLE_ONLY or self.value == self.DELIVERABLE_ONLY:
                # 只要有一个仓单尚未发货
                query = query.filter(models.Order.sub_order_list.any(
                    models.SubOrder.store_bill_list.any(
                        and_(models.StoreBill.weight > 0,
                             models.StoreBill.delivery_task_id == None))))
                if self.value == self.ACCOUNTABLE_ONLY: # 可盘点的订单要求所有的工单都已经生产完毕
                    # 所有的子订单都已经排产 == 不存在子订单，其剩余质量>0
                    query = query.filter(
                        ~models.Order.sub_order_list.any(
                            models.SubOrder.remaining_quantity > 0))
                    # 所有的子订单的工单都已经生成完毕==不存在子订单，其有工单未完成
                    query = query.filter(~models.Order.sub_order_list.any(
                        models.SubOrder.work_command_list.any(
                            models.WorkCommand.status != constants.work_command
                            .STATUS_FINISHED)))
            elif self.value == self.UNDISPATCHED_ONLY:
                query = query.filter(~models.Order.dispatched)
            elif self.value == self.WARNING_ONLY:
                # 所有的子订单都已经排产 == 不存在子订单，其剩余质量>0
                query = query.filter(
                    ~models.Order.sub_order_list.any(
                        models.SubOrder.remaining_quantity > 0))
                # 所有的子订单的工单都已经生成完毕==不存在子订单，其有工单未完成
                query = query.filter(~models.Order.sub_order_list.any(
                    models.SubOrder.work_command_list.any(
                        models.WorkCommand.status != constants.work_command
                        .STATUS_FINISHED)))
                

        return query

category_filter = CategoryFilter("category", name=u"是", options=[(CategoryFilter.UNDISPATCHED_ONLY, u"仅展示待下发订单"), 
        (CategoryFilter.DELIVERABLE_ONLY, u"仅展示可发货订单"), (CategoryFilter.ACCOUNTABLE_ONLY, u"仅展示可盘点订单")],
        hidden=True)


def only_finished_filter_test(col):
    manufacturing_status_set = {constants.work_command.STATUS_ASSIGNING,
                                constants.work_command.STATUS_ENDING,
                                constants.work_command.STATUS_LOCKED}
    return col.any(or_(SubOrder.work_command_list.any(WorkCommand.status.in_(manufacturing_status_set)), SubOrder.remaining_quantity>0))

only_unfinished_filter = filters.Only('sub_order_list', display_col_name=u'仅展示未生产完毕订单', test=only_finished_filter_test, notation='__unfinished_only')

