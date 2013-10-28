# -*- coding: UTF-8 -*-
from collections import OrderedDict
from flask import url_for, request

from flask.ext.databrowser import ModelView, filters, column_spec
from flask.ext.login import login_required
from flask.ext.principal import PermissionDenied
from werkzeug.utils import cached_property
from litefac import constants

from litefac.models import WorkCommand, Order, SubOrder
from litefac.apis.manufacture import get_wc_status_list, get_status_list, get_handle_type_list
from litefac.permissions import SchedulerPermission


class WorkCommandView(ModelView):
    __list_columns__ = ["id", "sub_order.order.customer_order_number", "department", "team", "org_weight", "org_cnt",
                        "sub_order.unit", "urgent", "sub_order.returned", "tech_req", "handle_type", "status",
                        "procedure", "previous_procedure", "order.goods_receipt.customer"]

    __column_labels__ = {"id": u"编号", "department": u"车间", "team": u"班组", "sub_order.unit": u"单位",
                         "sub_order.returned": u"退镀", "urgent": u"加急", "org_weight": u"重量（公斤）", "org_cnt": u"数量",
                         "handle_type": u"处理类型", "tech_req": u"技术要求", "status": u"状态", "procedure": u"工序",
                         "previous_procedure": u"上道工序", "sub_order.order.customer_order_number": u"订单编号",
                         "sub_order": u"子订单编号", "order.goods_receipt.customer": u"客户"}

    __default_order__ = ("id", "desc")

    __sortable_columns__ = ["sub_order.order.customer_order_number", "urgent", "sub_order.returned"]

    def preprocess(self, obj):
        from litefac import apis
        return apis.manufacture.WorkCommandWrapper(obj)

    def patch_row_attr(self, idx, row):
        if row.status != constants.work_command.STATUS_FINISHED and (row.urgent or row.sub_order.returned):
            return {"class":"error", "title":u"退镀或加急"}

    from datetime import datetime, timedelta
    today = datetime.today()
    yesterday = today.date()
    week_ago = (today - timedelta(days=7)).date()
    _30days_ago = (today - timedelta(days=30)).date()

    class In_Filter(filters.BaseFilter):
        __notation__ = "__in_ex"

        def __operator__(self, attr, value):
            return attr.in_(set(value))

    __column_filters__ = [
        In_Filter("status", u"是", options=[i[:2] for i in get_status_list()], display_col_name=u"状态"),
        filters.BiggerThan("create_time", name=u"在", display_col_name=u"创建时间",
                           options=[(yesterday, u'一天内'), (week_ago, u'一周内'), (_30days_ago, u'30天内')]),
        filters.Contains("sub_order.order.customer_order_number", name=u"包含", display_col_name=u"订单编号"),
        filters.EqualTo("sub_order.order.id", name="", hidden=True),
        filters.Only("urgent", display_col_name=u"只展示加急", test=lambda v: v == True, notation="__urgent"),
        filters.Only("sub_order.returned", display_col_name=u"只展示退镀", test=lambda v: v == True, notation="__returned"),
        filters.EqualTo("department", u"是")
    ]

    __column_formatters__ = {
        "status": lambda v, model: get_wc_status_list().get(v)[0],
        "department": lambda v, model: v if v else "",
        "team": lambda v, model: v if v else "",
        "sub_order.returned": lambda v, model: u"是" if v else u"否",
        "urgent": lambda v, model: u"是" if v else u"否",
        "procedure": lambda v, model: v if v else "",
        "previous_procedure": lambda v, model: v if v else "",
        "handle_type": lambda v, model: get_handle_type_list().get(v, u"未知")
    }

    def repr_obj(self, obj):
        return u"""
        <span>
        %(wc)s - <small>%(customer)s</small>
        <small class='pull-right muted'>
        %(datetime)s
        </small>
        </span>
        """ % {"wc": unicode(obj), "customer": obj.order.goods_receipt.customer, "datetime": obj.create_time.strftime("%m-%d %H:%M")}

    def try_create(self):
        raise PermissionDenied

    @login_required
    def try_view(self, processed_objs=None):
        pass

    def try_edit(self, processed_objs=None):
        SchedulerPermission.test()
        if processed_objs and processed_objs[
            0].status == constants.work_command.STATUS_DISPATCHING:
            return True
        else:
            raise PermissionDenied


    def edit_hint_message(self,obj, read_only=False):
        if read_only:
            if not SchedulerPermission.can():
                return u"无修改订单的权限"
            else:
                return u"工单%d已进入生产流程，不能修改" % obj.id
        else:
            return super(WorkCommandView, self).edit_hint_message(obj, read_only)

    def get_customized_actions(self, processed_objs=None):
        from .actions import schedule_action, retrieve_action

        def _get_status_filter(desc):
            for i in get_status_list():
                if i[1] == desc:
                    return i[0]
            else:
                return None

        if processed_objs:
            if all(schedule_action.test_enabled(obj) == 0 for obj in processed_objs):
                return [schedule_action]
            elif all(retrieve_action.test_enabled(obj) == 0 for obj in processed_objs):
                return [retrieve_action]
        else:
            if self.__column_filters__[0].value == unicode(_get_status_filter(u"待生产")):
                return [schedule_action]
            elif self.__column_filters__[0].value == unicode(_get_status_filter(u"生产中")):
                return [retrieve_action]
            elif self.__column_filters__[0].has_value:
                return [schedule_action, retrieve_action]
        return []

    def get_form_columns(self, obj=None):

        form_columns = OrderedDict()
        c = column_spec.ColumnSpec("", formatter=lambda v, obj: u"%s-%s" % (v.id, v.cause_name) if v else "")

        form_columns[u"工单信息"] = [column_spec.ColumnSpec("id"), column_spec.ColumnSpec("org_weight"),
                                 column_spec.ColumnSpec("org_cnt"), column_spec.ColumnSpec("sub_order.unit"),
                                 column_spec.ColumnSpec("sub_order.spec", label=u"规格"),
                                 column_spec.ColumnSpec("sub_order.type", label=u"型号"),
                                 "urgent", "sub_order.returned", "tech_req",
                                 column_spec.ColumnSpec("cause_name", label=u"产生原因"),
                                 column_spec.ColumnSpec("previous_work_command", label=u"上级工单",
                                                        formatter=lambda v, obj: u"%s-%s" % (
                                                            v.id, v.cause_name) if v else ""),
                                 column_spec.ListColumnSpec("next_work_command_list", label=u"下级工单",
                                                            item_col_spec=c),
                                 column_spec.PlaceHolderColumnSpec("log_list", label=u"日志",
                                                                   template_fname="logs-snippet.html")
        ]
        form_columns[u"加工信息"] = [column_spec.ColumnSpec("department"),
                                     column_spec.ColumnSpec("team"), "procedure",
                                     column_spec.ColumnSpec("previous_procedure"),
                                     column_spec.ColumnSpec("processed_weight", label=u"工序后重量"),
                                     column_spec.ColumnSpec("processed_cnt", label=u"工序后数量"),
                                     column_spec.ColumnSpec("status_name", label=u"状态"),
                                     column_spec.ColumnSpec("completed_time", label=u"生产结束时间"),
                                     column_spec.ColumnSpec("handle_type", label=u"处理类型",
                                                            formatter=lambda v, obj: get_handle_type_list().get(v, u"未知"))]
        if obj and obj.qir_list:
            from litefac.apis.quality_inspection import get_QI_result_list
            from litefac.portal.quality_inspection.views import qir_model_view
            def result(qir):
                for i in get_QI_result_list():
                    if qir.result == i[0]:
                        status =  i[1]
                        break
                else:
                    status = u"未知"
                return u"<a href='%s'>质检单%s%s了%s（公斤）</a>" % (
                qir_model_view.url_for_object(qir, url=request.url), qir.id, status, qir.weight)

            form_columns[u"质检信息"] = [column_spec.ListColumnSpec("qir_list", label=u"质检结果",
                                                                formatter=lambda v, obj: [result(qir) for qir in v])]

        form_columns[u"订单信息"] = [ column_spec.ColumnSpec("sub_order"),
                            column_spec.ColumnSpec("sub_order.order", label=u"订单号")]
        return form_columns

work_command_view = WorkCommandView(WorkCommand)
# from flask import (request, abort, redirect, url_for, render_template, json,
#                    flash)
# from flask.ext.login import current_user
# from wtforms import Form, HiddenField, TextField, BooleanField, \
#     IntegerField, validators
# from litefac.portal.manufacture import manufacture_page
# import litefac.constants as constants
# from litefac.utilities import decorators, Pagination
# from litefac.permissions.work_command import view_work_command
#
#
# @manufacture_page.route("/")
# def index():
#     return redirect(url_for("manufacture.work_command_list"))
#
#
# @manufacture_page.route("/work-command-list", methods=["POST", "GET"])
# @decorators.templated("/manufacture/work-command-list.html")
# @decorators.nav_bar_set
# def work_command_list():
#     decorators.permission_required(view_work_command)
#     page = request.args.get('page', 1, type=int)
#     status = request.args.get('status', 1, type=int)
#     harbor = request.args.get('harbor', u"全部")
#     order_id = request.args.get('order_id', None)
#     status_list = []
#     schedule_button = False
#     retrieve_button = False
#     if status == constants.work_command.STATUS_DISPATCHING:
#         status_list.extend(
#             [constants.work_command.STATUS_REFUSED])
#         schedule_button = True
#     elif status == constants.work_command.STATUS_ENDING:
#         status_list.extend(
#             [constants.work_command.STATUS_LOCKED,
#              constants.work_command.STATUS_ASSIGNING])
#         retrieve_button = True
#     status_list.append(status)
#     import litefac.apis as apis
#
#     work_commands, total_cnt = apis.manufacture.get_work_command_list(
#         status_list=status_list, harbor=harbor, order_id=order_id,
#         start=(page - 1) * constants.UNLOAD_SESSION_PER_PAGE,
#         cnt=constants.UNLOAD_SESSION_PER_PAGE)
#     pagination = Pagination(page, constants.UNLOAD_SESSION_PER_PAGE, total_cnt)
#     param_dic = {'titlename': u'工单列表', 'pagination': pagination,
#                  'status': status, 'work_command_list': work_commands,
#                  'harbor': harbor, 'schedule': schedule_button,
#                  'retrieve': retrieve_button,
#                  'status_list': apis.manufacture.get_status_list(),
#                  'harbor_list': apis.harbor.get_harbor_list(),
#                  'all_status': dict(
#                      [(name, getattr(constants.work_command, name)) for name in
#                       constants.work_command.__dict__ if
#                       name.startswith("STATUS")]),
#     }
#     return param_dic
#
#
# @manufacture_page.route("/work-command/<id_>")
# @decorators.templated("/manufacture/work-command.html")
# @decorators.nav_bar_set
# def work_command(id_):
#     decorators.permission_required(view_work_command)
#     import litefac.apis as apis
#
#     wc = apis.manufacture.get_work_command(id_)
#     if not wc:
#         abort(404)
#     return {"work_command": wc,
#             "backref": request.args.get("backref")}
#
#
# @manufacture_page.route('/schedule', methods=['GET', 'POST'])
# @decorators.nav_bar_set
# def schedule():
#     import litefac.apis as apis
#
#     if request.method == 'GET':
#         decorators.permission_required(view_work_command)
#
#         def _wrapper(department):
#             return dict(id=department.id, name=department.name,
#                         procedure_list=[dict(id=p.id, name=p.name) for p in
#                                         department.procedure_list])
#
#         work_command_id_list = request.args.getlist("work_command_id")
#         department_list = apis.manufacture.get_department_list()
#         from litefac.basemain import nav_bar
#
#         if 1 == len(work_command_id_list):
#             work_command = apis.manufacture.get_work_command(
#                 work_command_id_list[0])
#             return render_template("manufacture/schedule-work-command.html",
#                                    **{'titlename': u'排产',
#                                       'department_list': [_wrapper(d) for d in
#                                                           department_list],
#                                       'work_command': work_command,
#                                       'nav_bar': nav_bar
#                                    })
#         else:
#             work_command_list = [apis.manufacture.get_work_command(id)
#                                  for id in work_command_id_list]
#             default_department_id = None
#
#
#             from litefac.utilities.functions import deduplicate
#
#             department_set = deduplicate(
#                 [wc.department for wc in work_command_list], lambda x: x.name)
#             if len(department_set) == 1: # 所有的工单都来自于同一个车间
#                 default_department_id = department_set.pop().id
#
#             param_dic = {'titlename': u'批量排产',
#                          'department_list': [_wrapper(d) for d in
#                                              department_list],
#                          'work_command_list': work_command_list,
#                          'default_department_id': default_department_id,
#                          'nav_bar': nav_bar
#             }
#             return render_template("/manufacture/batch-schedule.html",
#                                    **param_dic)
#     else: # POST
#         from litefac.permissions.work_command import schedule_work_command
#
#         decorators.permission_required(schedule_work_command, ("POST",))
#         form = WorkCommandForm(request.form)
#         if form.validate():
#             department = apis.manufacture.get_department(
#                 form.department_id.data)
#             if not department:
#                 abort(404)
#             work_command_id_list = form.id.raw_data
#             for work_command_id in work_command_id_list:
#                 work_command = apis.manufacture.get_work_command(
#                     int(work_command_id))
#
#                 if work_command:
#                     d = dict(tech_req=form.tech_req.data,
#                              urgent=form.urgent.data,
#                              department_id=department.id,
#                     )
#                     if form.procedure_id.data:
#                         d.update(procedure_id=form.procedure_id.data)
#
#                     work_command.go(actor_id=current_user.id,
#                                     action=constants.work_command.ACT_DISPATCH,
#                                     **d)
#                 else:
#                     abort(404)
#             flash(u"工单(%s)已经被成功排产至车间(%s)" %
#                   (",".join(work_command_id_list), department.name))
#             return redirect(
#                 form.url.data or url_for("manufacture.work_command_list"))
#         else:
#             return render_template("result.html", error_content=form.errors)
#
# @manufacture_page.route('/retrieve', methods=['POST'])
# def retrieve():
#     import litefac.apis as apis
#
#     work_command_id_list = request.form.getlist('work_command_id', type=int)
#     for id in work_command_id_list:
#         try:
#             apis.manufacture.WorkCommandWrapper.get_work_command(id).go(
#                 actor_id=current_user.id,
#                 action=constants.work_command.ACT_RETRIEVAL)
#         except ValueError as e:
#             return unicode(e), 403
#         except AttributeError:
#             abort(404)
#     flash(u"回收工单%s成功" % ",".join(str(id_) for id_ in work_command_id_list))
#     return redirect(
#         request.form.get('url', url_for('manufacture.work_command_list')))
#
#
# @manufacture_page.route('/qir-work-command-list')
# @decorators.templated('/manufacture/quality-inspection-work-command-list.html')
# @decorators.nav_bar_set
# def QI_work_command_list():
#     page = request.args.get('page', 1, type=int)
#     department_id = request.args.get('department', type=int)
#     from litefac import apis
#
#     work_command_list, total_cnt = apis.manufacture.get_work_command_list(
#         status_list=[constants.work_command.STATUS_FINISHED],
#         department_id=department_id, normal=True)
#     pagination = Pagination(page, constants.UNLOAD_SESSION_PER_PAGE, total_cnt)
#     return {'titlename': u'工单列表', 'work_command_list': work_command_list,
#             'pagination': pagination, 'department': department_id,
#             'department_list': apis.manufacture.get_department_list()
#     }
#
#
# @manufacture_page.route('/qir-list')
# @decorators.templated('/manufacture/quality-inspection-report-list.html')
# @decorators.nav_bar_set
# def QI_report_list():
#     work_command_id = request.args.get("id", type=int)
#     if work_command_id:
#         from litefac import apis
#
#         work_command = apis.manufacture.get_work_command(work_command_id)
#         qir_list, total_cnt = apis.quality_inspection.get_qir_list(
#             work_command_id)
#         return {'titlename': u'质检单', 'qir_list': qir_list,
#                 'work_command': work_command,
#                 'qir_result_list': apis.quality_inspection.get_QI_result_list()}
#     else:
#         abort(403)
#
#
# class WorkCommandForm(Form):
#     id = HiddenField('id', [validators.required()])
#     url = HiddenField('url')
#     procedure_id = IntegerField('procedure_id')
#     department_id = IntegerField('department_id', [validators.required()])
#     tech_req = TextField('tech_req')
#     urgent = BooleanField('urgent')
#
