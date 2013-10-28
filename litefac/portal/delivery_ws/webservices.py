# -*- coding: UTF-8 -*-
import json
from datetime import datetime

from flask import request
from flask.ext.login import current_user
from flask.ext.principal import PermissionDenied

import yawf

from litefac.utilities import _
from litefac.portal.delivery_ws import delivery_ws
from litefac.utilities import to_timestamp, get_or_404
from litefac.utilities.decorators import (webservice_call, login_required_webservice,
                                           permission_required_webservice)
import litefac.apis as apis
from litefac import models
from litefac import database
from litefac import constants
from litefac.permissions.roles import LoaderPermission


@delivery_ws.route("/delivery-session-list", methods=["GET"])
@webservice_call("json")
@login_required_webservice
def delivery_session_list():
    """
    get **unfinished** delivery sessions from database, accept no arguments
    """
    import litefac.apis as apis
    delivery_sessions, total_cnt = apis.delivery.get_delivery_session_list(unfinished_only=True)
    data = [{'plateNumber': ds.plate, 'sessionID': ds.id, 'isLocked': int(ds.is_locked)} for ds in
            delivery_sessions]
    return json.dumps(data)


@delivery_ws.route("/delivery-session", methods=["GET"])
@webservice_call("json")
@login_required_webservice
def delivery_session():
    """
    get delivery session from database
    """
    _id = request.args.get("id", type=int)
    if not _id:
        return _(u"需要id字段"), 403
    import litefac.apis as apis

    ds = apis.delivery.get_delivery_session(_id)
    if not ds:
        return _(u"没有如下发货会话") + str(_id), 404
    ret = dict(id=ds.id, plate=ds.plate)
    # store_bills是个两层结构，第一层是order，第二层主键是suborder
    store_bills = {}
    for sb in ds.store_bill_list:
        if not sb.delivery_task: # not delivered yet
            sub_order_2_store_bill = store_bills.setdefault(str(sb.sub_order.order.customer_order_number), {})
            sb_list = sub_order_2_store_bill.setdefault(sb.sub_order.id, [])
            sb_list.append(dict(id=sb.id, harbor=sb.harbor.name,
                                product_name=sb.product_name,
                                spec=sb.sub_order.spec,
                                type=sb.sub_order.type,
                                customer_name=sb.customer.name,
                                pic_url=sb.pic_url, unit=sb.sub_order.unit,
                                weight=sb.weight))
    ret.update(store_bills=store_bills)
    return json.dumps(ret)


@delivery_ws.route("/delivery-task", methods=["POST"])
@webservice_call("json")
@permission_required_webservice(LoaderPermission)
def delivery_task():
    is_finished = request.args.get("is_finished", type=int)
    remain = request.args.get("remain", type=int)

    json_sb_list = json.loads(request.data)
    if len(json_sb_list) == 0:
        return _(u"至少需要一个仓单"), 403
    finished_store_bill_id_list = []
    unfinished_store_bill_id_list = []
    for json_sb in json_sb_list:
        if json_sb["is_finished"]:
            try:
                finished_store_bill_id_list.append(int(json_sb["store_bill_id"]))
            except ValueError:
                return _(u"仓单id只能为非整数"), 403
        else:
            try:
                unfinished_store_bill_id_list.append(int(json_sb["store_bill_id"]))
            except ValueError:
                return _(u"仓单id只能为非整数"), 403
    if len(unfinished_store_bill_id_list) > 1:
        return _(u"最多只有一个仓单可以部分完成"), 403
    if unfinished_store_bill_id_list:
        if not remain:
            return _(u"需要remain字段"), 403

    delivery_session_id = request.args.get("sid", type=int)

    if yawf.token_bound(constants.work_flow.DELIVERY_TASK_WITH_ABNORMAL_WEIGHT, str(delivery_session_id)):
        return u'本卸货会话有待处理的工作流，请先敦促工作人员处理该工作流', 403

    ds = apis.delivery.get_delivery_session(delivery_session_id)
    if not ds:
        return _(u"需要发货会话字段"), 403
    id_list = [store_bill.id for store_bill in ds.store_bill_list]
    for id_ in finished_store_bill_id_list + unfinished_store_bill_id_list:
        if id_ not in id_list:
            return _(u"仓单%s未关联到发货会话%s" % (id_, delivery_session_id)), 403

    unfinished_store_bill = get_or_404(models.StoreBill,
                                       unfinished_store_bill_id_list[0]) if unfinished_store_bill_id_list else None
    if unfinished_store_bill and apis.delivery.store_bill_remain_unacceptable(unfinished_store_bill, remain):
        try:
            doc = database.codernity_db.insert(dict(delivery_session_id=delivery_session_id,
                                                    remain=remain,
                                                    finished_store_bill_id_list=finished_store_bill_id_list,
                                                    unfinished_store_bill_id=unfinished_store_bill.id,
                                                    loader_id=current_user.id,
                                                    is_last_task=is_finished))
            # 保存token，以避免重复提交工作流, 显然，对于一个卸货会话而言，只能同时存在一个正在处理的工作流
            work_flow = yawf.new_work_flow(constants.work_flow.DELIVERY_TASK_WITH_ABNORMAL_WEIGHT,
                                           lambda work_flow: models.Node(work_flow=work_flow,
                                                                         name=u"生成异常剩余重量的发货任务",
                                                                         policy_name='CreateDeliveryTaskWithAbnormalWeight'),
                                           tag_creator=lambda work_flow: doc['_id'], token=str(delivery_session_id))
            work_flow.start()
        except yawf.exceptions.WorkFlowDelayed, e:
            return "", 201
    else:
        finished_store_bill_list = [get_or_404(models.StoreBill, store_bill_id) for store_bill_id in
                                    finished_store_bill_id_list]
        try:
            dt = create_delivery_task(ds, remain, finished_store_bill_list, unfinished_store_bill,
                                      current_user, is_finished)
            ret = dict(id=dt.actor_id, actor_id=dt.actor_id, store_bill_id_list=dt.store_bill_id_list)
            return json.dumps(ret)
        except KeyError:
            return _(u"不能添加发货任务"), 403
        except (ValueError, PermissionDenied) as e:
            return unicode(e), 403


def create_delivery_task(ds, remain, finished_store_bill_id_list, unfinished_store_bill, loader,
                         is_finished):
    from litefac.portal.delivery.fsm import fsm

    fsm.reset_obj(ds)
    fsm.next(constants.delivery.ACT_LOAD, loader)
    dt = apis.delivery.new_delivery_task(loader.id, finished_store_bill_id_list, unfinished_store_bill, remain)
    if is_finished:  # 发货会话结束
        dt.update(is_last=True)
        dt.delivery_session.update(finish_time=to_timestamp(datetime.now()))
    return dt
