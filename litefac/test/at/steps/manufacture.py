# -*- coding: UTF-8 -*-
import json
from StringIO import StringIO

from flask import url_for
from flask.ext.login import current_user
from sqlalchemy import and_
from pyfeature import step

import litefac
from litefac import models
from litefac.basemain import app
from litefac.test.utils import login, client_login
from litefac.constants import (quality_inspection as qi_const,
                                work_command as wc_const)


@step(u'调度员对子订单进行预排产(\d+)公斤')
def _(step, weight, sub_order):
    with app.test_request_context():
        with app.test_client() as c:
            login('s', 's', c)
            rv = c.post('/order/work-command',
                        data=dict(sub_order_id=sub_order.id,
                                  schedule_weight=weight))
            assert rv.status_code == 302


@step(u'一条重量是(\d+)公斤的工单生成了')
def _(step, weight, sub_order):
    model = models.WorkCommand
    return model.query.filter(and_(model.org_weight == weight,
                                   model.sub_order_id == sub_order.id)).one()


@step(u'原子订单的剩余重量是(\d+)公斤')
def _(step, weight, sub_order):
    assert int(sub_order.resync().remaining_quantity) == int(weight)


@step(u'调度员将工单排产给车间')
def _(step, wc, department):
    with app.test_request_context():
        with app.test_client() as c:
            login('s', 's', c)
            rv = c.post('/manufacture/schedule',
                        data=dict(department_id=department.id, id=wc.id))
            assert rv.status_code == 302


@step(u'车间主任将看到工单')
def _(step, wc, department):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('dl', 'dl', c)
            url = '/manufacture_ws/work-command-list?department_id=%s&\
status=%d&auth_token=%s'
            rv = c.get(url % (department.id,
                              litefac.constants.work_command.STATUS_ASSIGNING,
                              auth_token))
            assert rv.status_code == 200
            d = json.loads(rv.data)['data'][0]
            assert d['customerName'] == \
                wc.sub_order.order.goods_receipt.customer.name
            assert d['department']['id'] == department.id
            assert d['department']['name'] == department.name
            assert d['id'] == wc.id
            assert d['orderID'] == wc.sub_order.order.id
            assert d['subOrderId'] == wc.sub_order.id
            assert d['orgWeight'] == wc.org_weight


@step(u'车间主任将工单分配到班组')
def _(step, wc, department, team):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('dl', 'dl', c)
            url = '/manufacture_ws/work-command/%d?action=%d&team_id=%s\
&auth_token=%s'
            rv = c.put(url % (wc.id,
                              litefac.constants.work_command.ACT_ASSIGN,
                              team.id,
                              auth_token))
            assert rv.status_code == 200


@step(u'班组长将看到工单')
def _(step, wc, team):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('tl', 'tl', c)
            rv = c.get('/manufacture_ws/work-command-list?team_id=%s&status=%d&auth_token=%s' % (team.id, litefac.constants.work_command.STATUS_ENDING, auth_token))
            assert rv.status_code == 200
            d = json.loads(rv.data)['data'][0]
            assert d['customerName'] == wc.sub_order.order.goods_receipt.customer.name
            assert d['team']['id'] == team.id
            assert d['team']['name'] == team.name
            assert d['id'] == wc.id
            assert d['orderID'] == wc.sub_order.order.id
            assert d['subOrderId'] == wc.sub_order.id
            assert d['orgWeight'] == wc.org_weight



@step(u'班组长增加重量(\d+)公斤, 并且结束')
def _(step, weight, wc):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('tl', 'tl', c)
            rv = c.put('/manufacture_ws/work-command/%d?action=%d&weight=%d&is_finished=1&auth_token=%s' % (wc.id, litefac.constants.work_command.ACT_ADD_WEIGHT, int(weight), auth_token))
            assert rv.status_code == 200

@step(u'班组长增加重量(\d+)公斤$')
def _(step, weight, wc):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('tl', 'tl', c)
            rv = c.put('/manufacture_ws/work-command/%d?action=%d&weight=%d&auth_token=%s' % (wc.id, litefac.constants.work_command.ACT_ADD_WEIGHT, int(weight), auth_token))
            assert rv.status_code == 200

@step(u'工单的工序后重量是(\d+)公斤')
def _(step, weight, wc):
    assert wc.resync().processed_weight == int(weight)

@step(u'质检员可以看到工单')
def _(step, wc, team):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('qi', 'qi', c)
            rv = c.get('/manufacture_ws/work-command-list?status=%d&auth_token=%s' % (litefac.constants.work_command.STATUS_QUALITY_INSPECTING, auth_token))
            assert rv.status_code == 200
            d = json.loads(rv.data)['data'][0]
            assert d['customerName'] == wc.sub_order.order.goods_receipt.customer.name
            assert d['team']['id'] == team.id
            assert d['team']['name'] == team.name
            assert d['id'] == wc.id
            assert d['orderID'] == wc.sub_order.order.id
            assert d['subOrderId'] == wc.sub_order.id
            assert d['orgWeight'] == wc.org_weight

@step(u'质检员全部通过该工单')
def _(step, wc):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('qi', 'qi', c)
            url = url_for('manufacture_ws.work_command',
                          work_command_id=wc.id,
                          action=wc_const.ACT_QI,
                          auth_token=auth_token)
            rv = c.put(url,
                       data={
                           '0.jpeg': (StringIO('foo jpg 0'), '0.jpeg'),
                           '1.jpeg': (StringIO('foo jpg 1'), '1.jpeg'),
                           'qirList':
                           json.dumps([{'result': qi_const.FINISHED,
                                        'weight': wc.processed_weight}])
                       })
            assert rv.status_code == 200
            url = url_for('manufacture_ws.work_command', work_command_id=wc.id,
                          auth_token=auth_token)
            rv = c.get(url)
            assert rv.status_code == 200
            d = json.loads(rv.data)
            assert len(d['qirList']) == 1
            qir_dict = d['qirList'][0]
            assert qir_dict['result'] == qi_const.FINISHED
            assert qir_dict['weight'] == wc.processed_weight
            assert qir_dict['quantity'] == wc.processed_weight
            assert qir_dict['actorId'] == current_user.id
            return qir_dict

@step(u'该工单已经结束')
def _(step, wc):
    assert wc.resync().status == litefac.constants.work_command.STATUS_FINISHED

@step(u'一条对应的仓单生成了')
def _(step, qir, harbor):
    model = models.StoreBill
    return model.query.filter(and_(model.qir_id==qir['id'],
                                   model.weight==qir['weight'],
                                   model.harbor_name==harbor.name)).one()


@step(u'质检员保存质检结果')
def _(step, wc):
    with app.test_client() as c:
        auth_token = client_login('qi', 'qi', c)
        url = url_for('manufacture_ws.quality_inspection_report_list',
                      work_command_id=wc.id,
                      auth_token=auth_token)
        qir_list = [{'result': qi_const.FINISHED,
                     'weight': wc.processed_weight}]
        rv = c.put(url,
                   data={
                       '0.jpeg': (StringIO('foo jpg 0'), '0.jpg'),
                       '1.jpeg': (StringIO('foo jpg 1'), '1.jpg'),
                       'qirList': json.dumps(qir_list)
                   })
        assert rv.status_code == 200
        return qir_list


@step(u'工单的质检报告列表正确保存了')
def _(step, wc, qir_list):
    with app.test_client() as c:
        auth_token = client_login('qi', 'qi', c)
        url = url_for('manufacture_ws.work_command', work_command_id=wc.id,
                      auth_token=auth_token)
        rv = c.get(url)
        assert rv.status_code == 200
        wc_dict = json.loads(rv.data)
        assert len(wc_dict['qirList']) == 1
        qir_dict1 = wc_dict['qirList'][0]
        qir_dict2 = qir_list[0]

        assert qir_dict1['result'] == qi_const.FINISHED
        assert qir_dict1['weight'] == qir_dict2['weight']
        # 标准类型的质检单，重量与数量相同
        assert qir_dict1['quantity'] == qir_dict2['weight']
        assert qir_dict1['actorId'] == current_user.id
