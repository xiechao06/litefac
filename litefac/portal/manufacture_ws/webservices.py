# -*- coding: UTF-8
import time
from datetime import datetime, date, timedelta
import json
import os
import types
from flask import request
from flask.ext.login import current_user
from flask.ext.babel import _
from wtforms import (Form, IntegerField, StringField, validators,
                     ValidationError)
import litefac
from litefac import apis
from litefac import models
from litefac.utilities import get_or_404
from litefac.basemain import app
import litefac.constants.work_command as wc_const
from litefac import constants
from litefac.portal.manufacture_ws import manufacture_ws
from litefac.utilities.decorators import (webservice_call,
                                           login_required_webservice,
                                           permission_required_webservice)
from litefac.utilities import to_timestamp, gen_qir_pic_path
from litefac.database import db
from litefac.permissions.roles import (TeamLeaderPermission,
                                        DepartmentLeaderPermission,
                                        QualityInspectorPermission)


def _qir2dict(qir):
    return dict(id=qir.id, actorId=qir.actor_id, quantity=qir.quantity,
                weight=qir.weight, result=qir.result,
                picUrl=qir.pic_url, smallPicUrl=qir.small_pic_url)


def _work_command_to_dict(wc):
    qirs, total_cnt = litefac.apis.quality_inspection.get_qir_list(wc.id)

    return dict(id=wc.id,
                customerName=wc.order.customer.name,
                department=dict(id=wc.department.id,
                                name=wc.department.name) if wc.department
                else "",
                isUrgent=1 if wc.urgent else 0,
                spec=wc.sub_order.spec,
                type=wc.sub_order.type,
                lastMod=to_timestamp(wc.last_mod),
                orderID=wc.sub_order.order_id,
                orderNum=wc.sub_order.order.customer_order_number,
                orderCreateTime=time.mktime(wc.sub_order.order.create_time.
                                            timetuple()),
                orderType=wc.sub_order.order_type,
                orgCount=wc.org_cnt,
                orgWeight=wc.org_weight,
                picPath=wc.pic_url,
                smallPicPath=wc.small_pic_url,
                previousProcedure=wc.previous_procedure.name if wc
                .previous_procedure else "",
                procedure=wc.procedure.name if wc.procedure else "",
                processedCount=wc.processed_cnt,
                processedWeight=wc.processed_weight or 0,
                productName=wc.sub_order.product.name,
                status=wc.status,
                subOrderId=wc.sub_order_id,
                team=dict(id=wc.team.id, name=wc.team.name) if wc.team else "",
                technicalRequirements=wc.tech_req,
                handleType=wc.handle_type,
                deduction=wc.deduction,
                unit=wc.unit,
                rejected=int(wc.sub_order.returned),
                qirList=[_qir2dict(qir) for qir in qirs])


@manufacture_ws.route("/work-command-list", methods=["GET"])
@webservice_call("json")
@login_required_webservice
def work_command_list():
    class _ValidationForm(Form):
        def validate_status(self, field):
            status_list = field.data.split(",")
            valid_status = [wc_const.STATUS_DISPATCHING,
                            wc_const.STATUS_ASSIGNING,
                            wc_const.STATUS_ENDING,
                            wc_const.STATUS_LOCKED,
                            wc_const.STATUS_REFUSED,
                            wc_const.STATUS_QUALITY_INSPECTING,
                            wc_const.STATUS_FINISHED]
            if not all(status.isdigit() and int(status) in valid_status for
                       status in status_list):
                raise ValidationError("status must be one of " +
                                      ", ".join(str(i) for i in valid_status))

        department_id = IntegerField(u"department id")
        team_id = IntegerField(u"team id")
        start = IntegerField(u"start")
        cnt = IntegerField(u"count")
        status = StringField(u"status", [validators.DataRequired()])

    form = _ValidationForm(request.args)
    if form.validate():
        status_list = [int(status) for status in form.status.data.split(',')]
        param_dict = dict(status_list=status_list)

        if len(status_list) == 1 and \
           status_list[0] == wc_const.STATUS_FINISHED:
            param_dict["date"] = datetime.now().date() - timedelta(days=1)
        if form.department_id.data is not None:
            param_dict.update(department_id=form.department_id.data)
        if form.team_id.data is not None:
            param_dict.update(team_id=form.team_id.data)
        if form.start.data is not None:
            param_dict.update(start=form.start.data)
        if form.cnt.data is not None:
            param_dict.update(cnt=form.cnt.data)

        wc_list, total_cnt = apis.manufacture.get_work_command_list(
            **param_dict)
        return json.dumps(
            dict(data=[_work_command_to_dict(wc) for wc in wc_list],
                 totalCnt=total_cnt))
    else:
        # we disable E1101, since it's a bug of pylint
        return str(form.errors), 412


@manufacture_ws.route("/team-list", methods=["GET"])
@webservice_call("json")
def team_list():
    department_id = request.args.get("department_id", type=int)
    if department_id is None:
        teams = litefac.models.Team.query.all()
        return json.dumps([dict(name=t.name, id=t.id) for t in teams])
    else:
        teams = apis.manufacture.get_team_list(department_id)
    return json.dumps([dict(name=t.name, id=t.id) for t in teams])


@manufacture_ws.route("/department-list", methods=["GET"])
@webservice_call("json")
def department_list():
    departments = litefac.models.Department.query.all()
    return json.dumps([dict(id=d.id, name=d.name,
                            team_id_list=[t.id for t in d.team_list])
                       for d in departments])


@manufacture_ws.route("/work-command/<work_command_id>",
                      methods=["GET", "PUT"])
@webservice_call("json")
def work_command(work_command_id):
    if request.method == 'PUT':
        action = request.args.get('action', type=int)
        if action in {wc_const.ACT_ASSIGN,
                      wc_const.ACT_REFUSE,
                      wc_const.ACT_AFFIRM_RETRIEVAL,
                      wc_const.ACT_REFUSE_RETRIEVAL}:
            permission = DepartmentLeaderPermission
        elif action in {wc_const.ACT_ADD_WEIGHT,
                        wc_const.ACT_END,
                        wc_const.ACT_CARRY_FORWARD,
                        wc_const.ACT_QUICK_CARRY_FORWARD}:
            permission = TeamLeaderPermission
        else:
            permission = QualityInspectorPermission

        func = permission_required_webservice(permission)(_work_command)
    else:
        func = login_required_webservice(_work_command)
    return func(work_command_id)


def _work_command(work_command_id):
    if request.method == 'GET':
        wc = get_or_404(models.WorkCommand, work_command_id)
        return json.dumps(_work_command_to_dict(wc))
    else:  # PUT
        class _ValidationForm(Form):
            def validate_team_id(self, field):
                if self.action.data == wc_const.ACT_ASSIGN:
                    if field.data is None:
                        raise ValidationError("team required when assigning \
work command")

            def validate_weight(self, field):
                if self.action.data == wc_const.ACT_ADD_WEIGHT or \
                   self.action.data == wc_const.ACT_AFFIRM_RETRIEVAL:
                    if field.data is None:
                        raise ValidationError(_("需要weight字段"))

            def validate_is_finished(self, field):
                if field.data is not None:
                    if field.data not in [0, 1]:
                        raise ValidationError("is finished should be 0 or 1")

            quantity = IntegerField(u"quantity")
            weight = IntegerField(u"weight")
            remain_weight = IntegerField(u"remain_weight")
            team_id = IntegerField(u"team id")
            action = IntegerField(u"action", [validators.DataRequired()])
            is_finished = IntegerField(u"is finished")
            deduction = IntegerField(u"deduction")

        form = _ValidationForm(request.args)
        if form.validate():
            if form.action.data == wc_const.ACT_ASSIGN:
                try:
                    wc = get_or_404(models.WorkCommand, work_command_id)
                    wc.go(actor_id=current_user.id, action=form.action.data,
                          team_id=form.team_id.data)
                except ValueError, e:
                    return unicode(e), 403
                result = wc
            elif form.action.data == wc_const.ACT_AFFIRM_RETRIEVAL:
                kwargs = {"weight": form.weight.data}
                try:
                    wc = get_or_404(models.WorkCommand, work_command_id)

                    if not wc.sub_order.measured_by_weight:
                        kwargs.update(quantity=form.quantity.data)
                    wc.go(actor_id=current_user.id, action=form.action.data,
                          **kwargs)
                except ValueError, e:
                    return unicode(e), 403
                result = wc
            elif form.action.data == wc_const.ACT_ADD_WEIGHT:
                kwargs = {"weight": form.weight.data}
                try:
                    wc = get_or_404(models.WorkCommand, work_command_id)

                    if not wc.sub_order.measured_by_weight:
                        kwargs.update(quantity=form.quantity.data)
                    wc.go(actor_id=current_user.id, action=form.action.data,
                          **kwargs)
                    if form.is_finished.data:
                        wc.go(actor_id=current_user.id,
                              action=wc_const.ACT_END)
                except ValueError, e:
                    return unicode(e), 403
                result = wc
            elif form.action.data == wc_const.ACT_QI:
                try:
                    wc = get_or_404(models.WorkCommand, work_command_id)

                    qir_pic_path_map = {}

                    for path, f in request.files.items():
                        idx = int(path.split(".")[0])
                        pic_path = gen_qir_pic_path(idx)
                        f.save(os.path.join(app.config["UPLOAD_FOLDER"], pic_path))
                        qir_pic_path_map[idx] = pic_path

                    qir_list = [dict(result=qir['result'],
                                     weight=qir['weight'],
                                     quantity=qir.get('quantity'),
                                     actor_id=current_user.id,
                                     pic_path=qir_pic_path_map.get(idx, ""))
                                for idx, qir in
                                enumerate(json.loads(request.form['qirList']))]
                    if wc.sub_order.order_type == \
                       constants.STANDARD_ORDER_TYPE:
                        for qir in qir_list:
                            qir['quantity'] = qir['weight']
                    else:
                        for qir in qir_list:
                            if qir['quantity'] is None:
                                return u'计件类型工单质检时必须上传数量', 403
                    wc.go(actor_id=current_user.id, action=form.action.data,
                          deduction=form.deduction.data or 0,
                          qir_list=qir_list)
                except ValueError, e:
                    return unicode(e), 403
                result = wc
            elif form.action.data in [wc_const.ACT_CARRY_FORWARD,
                                      wc_const.ACT_REFUSE_RETRIEVAL,
                                      wc_const.ACT_END,
                                      wc_const.ACT_REFUSE]:
                try:
                    wc_id_list = [int(wc_id) for wc_id in
                                  work_command_id.split(",")]
                except ValueError:
                    return "work command id should be integer", 403
                result = []
                # TODO may be it could be done batchly
                for _work_command_id in wc_id_list:
                    wc = get_or_404(models.WorkCommand, _work_command_id)

                    try:
                        wc.go(actor_id=current_user.id,
                              action=form.action.data)
                    except ValueError, e:
                        return unicode(e), 403
                    result.append(wc)
                if len(result) == 1:
                    result = result[0]
                    # pylint: enable=R0912
            elif form.action.data == wc_const.ACT_RETRIVE_QI:

                try:
                    wc = get_or_404(models.WorkCommand, work_command_id)

                    if wc.last_mod.date() < date.today():
                        return u'不能取消今天以前的质检单', 403

                    wc.go(actor_id=current_user.id, action=form.action.data)
                except ValueError, e:
                    return unicode(e), 403
                result = wc
            elif form.action.data == wc_const.ACT_QUICK_CARRY_FORWARD:
                try:
                    wc = get_or_404(models.WorkCommand, work_command_id)

                    if wc.processed_weight <= 0:
                        return u'未加工过的工单不能快速结转', 403

                    wc.go(actor_id=current_user.id, action=form.action.data)
                except ValueError, e:
                    return unicode(e), 403
                result = wc
            else:
                return "error action", 403
            if isinstance(result, types.ListType):
                return json.dumps([_work_command_to_dict(wc_) for wc_ in
                                   result])
            else:
                return json.dumps(_work_command_to_dict(result))
        else:
            return str(form.errors), 403


def _handle_delete():
    from litefac.apis import quality_inspection

    id_ = request.args.get("id", type=int)
    if not id_:
        return "id and required", 403
    try:
        return quality_inspection.remove_qi_report(id_=id_,
                                                   actor_id=current_user.id)
    except ValueError, e:
        return unicode(e), 403


@manufacture_ws.route("/off-duty", methods=["POST"])
@login_required_webservice
def off_duty():
    if not current_user.is_anonymous():
        cnt = 0
        from litefac.apis import manufacture

        for team in current_user.team_list:
            wc_list, total_cnt = manufacture.get_work_command_list(
                status_list=[wc_const.STATUS_ENDING],
                team_id=team.id)
            for wc in wc_list:
                try:
                    wc.go(actor_id=current_user.id,
                          action=wc_const.ACT_CARRY_FORWARD)
                    cnt += 1
                except ValueError, e:
                    return unicode(e), 403
        return str(cnt)
    else:
        return "actor id is required", 403


@manufacture_ws.route('/quality-inspection-report-list', methods=['PUT'])
@permission_required_webservice(QualityInspectorPermission)
def quality_inspection_report_list():

    work_command_id = request.args.get('work_command_id', type=int)
    wc = get_or_404(models.WorkCommand, work_command_id)

    qir_list = json.loads(request.form['qirList'])
    if wc.sub_order.order_type == constants.STANDARD_ORDER_TYPE:
        for qir in qir_list:
            qir['quantity'] = qir['weight']
    else:
        for qir in qir_list:
            if qir['quantity'] is None:
                return u'计件类型工单质检时必须上传数量', 403

    # clear the original qir list
    wc.qir_list = []
    qir_pic_path_map = {}

    for path, f in request.files.items():
        idx = int(path.split(".")[0])
        pic_path = gen_qir_pic_path(idx)
        f.save(os.path.join(app.config["UPLOAD_FOLDER"], pic_path))
        qir_pic_path_map[idx] = pic_path

    for idx, qir_dict in enumerate(qir_list):
        db.session.add(models.QIReport(wc.model, qir_dict['quantity'],
                                       qir_dict['weight'], qir_dict['result'],
                                       current_user.id,
                                       pic_path=qir_pic_path_map.get(idx, '')))
    db.session.commit()
    return ""
