#-*- coding:utf-8 -*-
from datetime import datetime

from flask.ext.babel import _
from lite_sm import StateMachine, State, InvalidAction

from litefac.exceptions import InvalidStatus
from litefac import constants, models
from litefac.utilities import action_name, status_name, do_commit


class WorkCommandState(State):
    status = "DEFAULT"

    def next(self, action):
        raise InvalidAction(_(u"%(status)s状态不允许进行%(action)s操作" %
                              {"action": action_name(action),
                               "status": status_name(self.status)}))


class StateDispatching(WorkCommandState):
    """
    the initial state
    """
    status = constants.work_command.STATUS_DISPATCHING

    def next(self, action):
        if action == constants.work_command.ACT_DISPATCH:
            return state_assigning
        else:
            raise InvalidAction(_(u"%(status)s状态不允许进行%(action)s操作" %
                                  {"action": action_name(action),
                                   "status": status_name(self.status)}))

    def side_effect(self, **kwargs):
        self.sm.obj.set_status(constants.work_command.STATUS_DISPATCHING)
        if self.last_status == constants.work_command.STATUS_LOCKED:
            # 根据车间主任之前填写的工序后重量/数量，将原有工单的重量修正后
            # 返回
            old_wc = self.sm.obj
            old_wc.org_weight -= kwargs["weight"]
            if old_wc.org_weight <= 0:
                # 至少保证为1， 这同时也意味着原有工单的重量不准确，所以不能
                # 进行回收
                old_wc.org_weight = 1
            processed_weight = kwargs["weight"]

            if old_wc.sub_order.order_type == constants.EXTRA_ORDER_TYPE:
                old_wc.org_cnt -= kwargs["quantity"]
                processed_quantity = kwargs["quantity"]
            else:
                old_wc.org_cnt = old_wc.org_weight
                processed_quantity = processed_weight
            if old_wc.org_cnt <= 0:
                # 至少保证为1， 这同时也意味着原有工单的数量不准确，所以不能
                # 进行回收
                old_wc.org_cnt = 1

            if processed_weight and processed_quantity:
                new_wc = models.WorkCommand(sub_order=old_wc.sub_order,
                                            org_weight=processed_weight,
                                            procedure=old_wc.procedure,
                                            urgent=old_wc.urgent,
                                            status=constants.work_command.STATUS_QUALITY_INSPECTING,
                                            department=old_wc.department,
                                            processed_weight=processed_weight,
                                            team=old_wc.team,
                                            previous_procedure=old_wc.previous_procedure,
                                            tag=old_wc.tag,
                                            tech_req=old_wc.tech_req,
                                            org_cnt=processed_quantity,
                                            processed_cnt=processed_quantity,
                                            pic_path=old_wc.pic_path,
                                            handle_type=old_wc.handle_type,
                                            previous_work_command=old_wc)
                do_commit(new_wc)

        self.sm.obj.department = None
        self.sm.obj.team = None


class StateRefused(WorkCommandState):
    """
    in fact, it is just an alias of STATUS_DISPATCHING
    """

    status = constants.work_command.STATUS_REFUSED

    def next(self, action):
        if action == constants.work_command.ACT_DISPATCH:
            return state_assigning
        else:
            raise InvalidAction(_(u"%(status)s状态不允许进行%(action)s操作" %
                                  {"action": action_name(action),
                                   "status": status_name(self.status)}))

    def side_effect(self, **kwargs):
        self.sm.obj.set_status(constants.work_command.STATUS_REFUSED)


class StateAssigning(WorkCommandState):
    status = constants.work_command.STATUS_ASSIGNING

    def next(self, action):
        if action == constants.work_command.ACT_ASSIGN:
            return state_ending
        elif action == constants.work_command.ACT_REFUSE:
            return state_refused
        elif action == constants.work_command.ACT_RETRIEVAL:
            return state_dispatching
        else:
            raise InvalidAction(_(u"%(status)s状态不允许进行%(action)s操作" %
                                  {"action": action_name(action),
                                   "status": status_name(self.status)}))

    def side_effect(self, **kwargs):
        self.sm.obj.set_status(constants.work_command.STATUS_ASSIGNING)
        if kwargs.get("department"):
            self.sm.obj.department = kwargs["department"]
        self.sm.obj.tech_req = kwargs["tech_req"]
        if kwargs.get("procedure_id"):
            self.sm.obj.procedure_id = kwargs.get("procedure_id")
        self.sm.obj.team = None
        if not self.sm.obj.department:
            raise InvalidStatus(_(u"%(status)s状态必须有department字段") % {
                "status": status_name(self.status)})


class StateEnding(WorkCommandState):
    status = constants.work_command.STATUS_ENDING

    def next(self, action):
        if action == constants.work_command.ACT_ADD_WEIGHT:
            return self
        elif action == constants.work_command.ACT_RETRIEVAL:
            return state_locked
        elif action == constants.work_command.ACT_END:
            return state_quality_inspecting
        elif action == constants.work_command.ACT_CARRY_FORWARD:
            if self.sm.obj.processed_cnt == 0: # carry forward COMPLETELY
                return state_assigning
            else:
                return state_quality_inspecting
        elif action == constants.work_command.ACT_QUICK_CARRY_FORWARD:
            return state_ending
        else:
            raise InvalidAction(_(u"%(status)s状态不允许进行%(action)s操作" %
                                  {"action": action_name(action),
                                   "status": status_name(self.status)}))

    def side_effect(self, **kwargs):
        if self.last_action == constants.work_command.ACT_QUICK_CARRY_FORWARD:
            old_wc = self.sm.obj

            new_wc = models.WorkCommand(sub_order=old_wc.sub_order,
                                        org_weight=old_wc.processed_weight,
                                        procedure=old_wc.procedure,
                                        status=constants.work_command
                                        .STATUS_QUALITY_INSPECTING,
                                        team=old_wc.team,
                                        department=old_wc.department,
                                        previous_procedure=old_wc
                                        .previous_procedure,
                                        tag=old_wc.tag,
                                        tech_req=old_wc.tech_req,
                                        org_cnt=old_wc.processed_cnt,
                                        pic_path=old_wc.pic_path,
                                        handle_type=old_wc.handle_type,
                                        processed_weight=old_wc.processed_weight,
                                        processed_cnt=old_wc.processed_cnt,
                                        previous_work_command=old_wc)
            new_wc.completed_time = datetime.now()

            remain_quantity = old_wc.org_cnt - old_wc.processed_cnt
            if remain_quantity <= 0:
                remain_quantity = 1
            remain_weight = int(
                self.sm.obj.unit_weight * remain_quantity)

            old_wc.org_cnt = remain_quantity
            old_wc.org_weight = remain_weight
            old_wc.processed_cnt = 0
            old_wc.processed_weight = 0
            do_commit([old_wc, new_wc])

        else:
            self.sm.obj.set_status(constants.work_command.STATUS_ENDING)
            if "team" in kwargs:  # when it comes by ACT_ASSIGN
                self.sm.obj.team = kwargs["team"]

            if self.last_status == constants.work_command.STATUS_ENDING:
                try:
                    self.sm.obj.processed_weight += kwargs["weight"]
                except KeyError:
                    raise InvalidAction(_(u"该操作需要weight字段"))
                if self.sm.obj.sub_order.order_type == constants.EXTRA_ORDER_TYPE:  # 计件类型
                    try:
                        self.sm.obj.processed_cnt += kwargs["quantity"]
                    except KeyError:
                        raise InvalidAction(_(u"该操作需要quantity字段"))
                else: # 普通类型
                    self.sm.obj.processed_cnt = self.sm.obj \
                        .processed_weight


class StateQualityInspecting(WorkCommandState):
    status = constants.work_command.STATUS_QUALITY_INSPECTING

    def next(self, action):
        if action == constants.work_command.ACT_QI:
            return state_finished
        else:
            raise InvalidAction(_(u"%(status)s状态不允许进行%(action)s操作" %
                                  {"action": action_name(action),
                                   "status": status_name(self.status)}))

    def side_effect(self, **kwargs):
        self.sm.obj.set_status(
            constants.work_command.STATUS_QUALITY_INSPECTING)
        if self.last_status == constants.work_command.STATUS_ENDING:
            if self.last_action == constants.work_command.ACT_CARRY_FORWARD:
                old_wc = self.sm.obj
                remain_quantity = old_wc.org_cnt - old_wc.processed_cnt
                if remain_quantity <= 0:
                    remain_quantity = 1
                remain_weight = int(
                    self.sm.obj.unit_weight * remain_quantity)
                new_wc = models.WorkCommand(sub_order=old_wc.sub_order,
                                            org_weight=remain_weight,
                                            procedure=old_wc.procedure,
                                            status=constants.work_command
                                            .STATUS_ASSIGNING,
                                            previous_procedure=old_wc
                                            .previous_procedure,
                                            tag=old_wc.tag,
                                            tech_req=old_wc.tech_req,
                                            org_cnt=remain_quantity,
                                            pic_path=old_wc.pic_path,
                                            handle_type=old_wc.handle_type,
                                            department=old_wc.department,
                                            previous_work_command=old_wc)

                old_wc.org_cnt -= new_wc.org_cnt  #: 实际工作的黑件数
                old_wc.org_weight -= new_wc.org_weight

                do_commit([new_wc, old_wc])

            self.sm.obj.completed_time = datetime.now()
            do_commit(self.sm.obj)
        elif self.last_status == constants.work_command.STATUS_FINISHED:
            old_wc = self.sm.obj
            from litefac.apis.quality_inspection import QIReportWrapper

            qir_list = [QIReportWrapper(qir) for qir in old_wc.qir_list]
            if not qir_list:
                raise InvalidAction(u'该工单没有质检报告，不能取消质检结果')
                # 若某个质检报告生成的仓单已经完全发货或者部分发货, 不能取消质检报告
            if any(qir.partly_delivered for qir in qir_list):
                raise InvalidAction(u'新生成的仓单已经发货，不能取消质检报告')
            generate_wc_list = [
                qi_report.generated_work_command for qi_report
                in qir_list if qi_report.generated_work_command]
            if any(wc.status not in [constants.work_command.STATUS_DISPATCHING,
                                     constants.work_command.STATUS_ASSIGNING,
                                     constants.work_command.STATUS_REFUSED]
                   for wc in generate_wc_list):
                raise InvalidAction(u'新生成的工单已经分配，不能取消质检报告')

            # 删除工单的质检报告中，完全没有发货的仓单
            models.StoreBill.query.filter(models.StoreBill.qir_id.in_(
                [qir.id for qir in qir_list])).delete("fetch")
            # 删除工单的质检报告生成的工单
            wc_id_list = [qir.generated_work_command_id for qir in qir_list]
            models.QIReport.query.filter(
                models.QIReport.work_command_id == old_wc.id).update(
                {"generated_work_command_id": None})
            models.WorkCommand.query.filter(
                models.WorkCommand.id.in_(wc_id_list)).delete(
                "fetch")
            old_wc.deduction_list = []


class StateFinished(WorkCommandState):
    status = constants.work_command.STATUS_FINISHED

    def next(self, action):
        if action == constants.work_command.ACT_RETRIVE_QI:
            return state_quality_inspecting
        else:
            raise InvalidAction(_(u"%(status)s状态不允许进行%(action)s操作" %
                                  {"action": action_name(action),
                                   "status": status_name(self.status)}))

    def side_effect(self, **kwargs):
        self.sm.obj.set_status(constants.work_command.STATUS_FINISHED)
        if self.last_status == constants.work_command.STATUS_QUALITY_INSPECTING:
            old_wc = self.sm.obj
            procedure = ""
            previous_procedure = ""
            handle_type = ""
            status = ""
            department = None

            from litefac.database import db

            old_wc.qir_list = []
            db.session.add_all([models.QIReport(old_wc,
                                                qir_dict['quantity'],
                                                qir_dict['weight'],
                                                qir_dict['result'],
                                                qir_dict['actor_id'],
                                                pic_path=qir_dict['pic_path']) for qir_dict in kwargs['qir_list']])

            for qir in old_wc.qir_list:
                if qir.result == constants.quality_inspection.FINISHED:
                    sb = models.StoreBill(qir)
                    if self.sm.obj.team:
                        sb.printed = True
                        sb.harbor = self.sm.obj.team.department.harbor_list[0]
                    db.session.add(sb)
                    continue
                elif qir.result == constants.quality_inspection.DISCARD:
                    # use QIReport as discard report
                    continue
                elif qir.result == constants.quality_inspection.NEXT_PROCEDURE:
                    handle_type = constants.work_command.HT_NORMAL
                    procedure = None
                    previous_procedure = old_wc.procedure
                    status = constants.work_command.STATUS_DISPATCHING
                    department = None
                elif qir.result == constants.quality_inspection.REPAIR:
                    handle_type = constants.work_command.HT_REPAIRE
                    procedure = old_wc.procedure
                    previous_procedure = old_wc.previous_procedure  # 可能有三道工序
                    status = constants.work_command.STATUS_ASSIGNING if old_wc.department else constants \
                        .work_command.STATUS_DISPATCHING
                    # 这个工单可能是由退货产生的。
                    department = old_wc.department
                elif qir.result == constants.quality_inspection.REPLATE:
                    handle_type = constants.work_command.HT_REPLATE
                    procedure = old_wc.procedure
                    previous_procedure = old_wc.previous_procedure
                    status = constants.work_command.STATUS_ASSIGNING if old_wc.department else constants \
                        .work_command.STATUS_DISPATCHING
                    department = old_wc.department
                new_wc = models.WorkCommand(sub_order=old_wc.sub_order,
                                            org_weight=qir.weight,
                                            status=status,
                                            tech_req=old_wc.tech_req,
                                            org_cnt=qir.quantity,
                                            procedure=procedure,
                                            previous_procedure=previous_procedure,
                                            pic_path=qir.pic_path,
                                            handle_type=handle_type,
                                            department=department,
                                            previous_work_command=old_wc)

                db.session.add(new_wc)
                qir.generated_work_command = new_wc
                db.session.add(qir)
            if kwargs.get("deduction"):
                db.session.add(models.Deduction(weight=kwargs["deduction"],
                                                work_command=old_wc,
                                                actor=kwargs["actor"],
                                                team=old_wc.team))
            db.session.commit()

class StateLocked(WorkCommandState):
    status = constants.work_command.STATUS_LOCKED

    def next(self, action):
        if action == constants.work_command.ACT_AFFIRM_RETRIEVAL:
            return state_dispatching
        elif action == constants.work_command.ACT_REFUSE_RETRIEVAL:
            # TODO should inform scheduler
            return state_ending
        else:
            raise InvalidAction(_(u"%(status)s状态不允许进行%(action)s操作" %
                                  {"action": action_name(action),
                                   "status": status_name(self.status)}))

    def side_effect(self, **kwargs):
        self.sm.obj.set_status(constants.work_command.STATUS_LOCKED)


class WorkCommandSM(StateMachine):
    def reset_obj(self, work_command):
        self.obj = work_command
        if work_command.status == constants.work_command.STATUS_DISPATCHING:
            self.set_current_state(state_dispatching)
        elif work_command.status == constants.work_command.STATUS_ASSIGNING:
            self.set_current_state(state_assigning)
        elif work_command.status == constants.work_command.STATUS_ENDING:
            self.set_current_state(state_ending)
        elif work_command.status == constants.work_command.STATUS_LOCKED:
            self.set_current_state(state_locked)
        elif work_command.status == constants.work_command.STATUS_QUALITY_INSPECTING:
            self.set_current_state(state_quality_inspecting)
        elif work_command.status == constants.work_command.STATUS_REFUSED:
            self.set_current_state(state_refused)
        elif work_command.status == constants.work_command.STATUS_FINISHED:
            self.set_current_state(state_finished)
        else:
            raise InvalidStatus(_(u"工单%(wc_id)d的状态%(status)d是非法的" %
                                  {"status": work_command.status,
                                   "wc_id": work_command.id}))

    def next(self, action, actor=None, *args, **kwargs):
        self.last_state = self.current_state
        self.last_action = action
        self.current_state = self.last_state.next(action)
        self.current_state.last_state = self.last_state
        self.current_state.action = action
        self.current_state.sm = self
        kwargs["actor"] = actor
        self.current_state.side_effect(*args, **kwargs)

        # notify the actors
        for actor_ in self.current_state.actors:
            self.sm.notify_next_actor(actor_)

        # log
        if self.logger:
            self.do_log(action, actor)

    def do_log(self, action, actor=None):
        if not actor:
            from flask.ext.login import current_user

            if current_user.is_authenticated():
                actor = current_user
        self.logger.info(u"操作: %s" % action_name(action),
                         extra={"obj": self.obj, "actor": actor,
                                "action": action_name(action),
                                "obj_pk": self.obj.id})


work_command_sm = WorkCommandSM()

state_dispatching = StateDispatching(work_command_sm)
state_assigning = StateAssigning(work_command_sm)
state_ending = StateEnding(work_command_sm)
state_locked = StateLocked(work_command_sm)
state_quality_inspecting = StateQualityInspecting(work_command_sm)
state_refused = StateRefused(work_command_sm)
state_finished = StateFinished(work_command_sm)
