# -*- coding: UTF-8 -*-
from flask import request, render_template
from flask.ext.login import current_user, login_required
from flask.ext.databrowser import ModelView, column_spec, action, filters
from flask.ext.principal import PermissionDenied

import yawf

from litefac.portal.work_flow import work_flow_page
from litefac.database import codernity_db
from litefac import models
from litefac.permissions.work_flow import handle_node


def _get_literally_status(status, obj):

    if status == yawf.constants.WORK_FLOW_EXECUTED:
        return u'执行完毕'
    elif status == yawf.constants.WORK_FLOW_APPROVED:
        return u'已批准(执行出错)'
    elif status == yawf.constants.WORK_FLOW_PROCESSING:
        return u'处理中'
    elif status == yawf.constants.WORK_FLOW_REFUSED:
        return u'拒绝'
    else:
        return u'未知'

class _RefuseNode(action.BaseAction):
    def test_enabled(self, node):
        if node.handle_time != None:
            return -2
        return 0

    def op(self, node):
        node.refuse()

    def get_forbidden_msg_formats(self):
        return {-2: u"该任务已经被处理"}

_refuse_node = _RefuseNode(u'拒绝')

class _ApproveNode(action.BaseAction):

    def test_enabled(self, node):
        if node.handle_time != None:
            return -2
        return 0

    def op(self, node):
        node.approve()

    def get_forbidden_msg_formats(self):
        return {-2: u"该任务已经被处理"}

_approve_node = _ApproveNode(u'批准')

class NodeModelView(ModelView):
   
    can_batchly_edit = False

    def try_create(self):
        raise PermissionDenied
    
    def try_edit(self, objs=None):
        handle_node.test()

    __list_columns__ = [column_spec.ColumnSpec('work_flow.id', label=u'工作流编号'),
                        column_spec.ColumnSpec('name', label=u'名称'),
                        column_spec.PlaceHolderColumnSpec('annotation', label=u'描述', 
                                                          template_fname='work-flow/permit-delivery-task-with-abnormal-weight-annotation.html'),
                        column_spec.ColumnSpec('create_time', label=u'创建时间', 
                                               formatter=lambda v, obj: v.strftime('%Y年%m月%d日 %H:%M').decode('utf-8')), 
                        column_spec.ColumnSpec('handle_time', label=u'处理时间', 
                                               formatter=lambda v, obj: v.strftime('%Y年%m月%d日 %H:%M').decode('utf-8') if v else '--'),
                        column_spec.ColumnSpec('work_flow.status', label=u'工作流状态',
                                               formatter=_get_literally_status )]

    __sortable_columns__ = ['work_flow.id', 'create_time']

    __default_order__ = ("create_time", "desc")

    __column_filters__ = [filters.EqualTo('work_flow.id', name=u'是', display_col_name=u'工作流编号'),
                          filters.Only('handle_time', display_col_name=u'仅展示待处理工作流', test=lambda col: col==None, default_value=True,
                                      notation="__only_unhandled"),
                         filters.Between('create_time', name=u'介于', display_col_name=u'创建时间')]

    def get_customized_actions(self, objs=None):
        return [_refuse_node, _approve_node]

    def __list_filters__(self):
        return [filters.EqualTo('handler_group_id', value=current_user.group.id), ]

node_model_view = NodeModelView(models.Node, u'工作流任务')
