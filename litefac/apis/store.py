# -*- coding: utf-8 -*-
"""
your file description here
"""
from litefac.apis.customer import CustomerWrapper
from litefac.models import Customer, StoreBill

def get_customer_list(time_span):
    """
    获取指定时间段内有仓单的客户
    """
    import litefac.apis as apis

    if time_span not in ["week", "month", "unlimited"]:
        raise ValueError(
            u"参数time_span值不能为%(time_span)s" % {"time_span": time_span})
    after = apis.order.get_should_after_date(time_span)
    return [CustomerWrapper(customer) for customer in
            Customer.query.join(StoreBill).filter(
                StoreBill.create_time > after).distinct()]
