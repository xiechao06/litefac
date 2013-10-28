# -*- coding: utf-8 -*-
import sys
from datetime import datetime

from werkzeug.datastructures import MultiDict
from flask import url_for, request
from flask.ext.babel import _
from sqlalchemy.orm.exc import NoResultFound
from wtforms import (Form, IntegerField, ValidationError, TextField,
                     BooleanField, validators)
from werkzeug.utils import cached_property

import litefac.constants as constants
from litefac import models
from litefac.apis import ModelWrapper
from litefac.utilities import do_commit

class WorkCommandWrapper(ModelWrapper):
    @property
    def qi(self):
        if self.qir_list:
            return self.qir_list[0].actor
        else:
            return None

    @property
    def finish_time(self):
        if self.status == constants.work_command.STATUS_FINISHED:
            return self.last_mod
        return None

    @cached_property
    def status_name(self):
        return get_wc_status_list().get(self.status)[0]

    @cached_property
    def status_describe(self):
        return get_wc_status_list().get(self.status)[1]

    @property
    def product(self):
        return self.sub_order.product

    @cached_property
    def handle_type_name(self):
        return get_handle_type_list().get(self.handle_type)

    @property
    def pic_url(self):
        if self.pic_path:
            return url_for("serv_pic", filename=self.pic_path)
        else:
            return ""

    @property
    def small_pic_url(self):
        return url_for("serv_small_pic", filename=self.pic_path) if self.pic_path else ""

    @cached_property
    def harbor(self):
        return self.sub_order.harbor

    @property
    def order(self):
        return self.sub_order.order

    @property
    def unit(self):
        return self.sub_order.unit

    @property
    def default_department(self):
        for d in get_department_list():
            if self.harbor in d.harbor_list:
                return d
        return None

    @property
    def delivered_weight(self):
        return sum(sum(sb.weight for sb in qir.store_bill_list if sb.delivered) for qir in self.qir_list)

    @property
    def to_delivery_weight(self):
        return sum(sum(sb.weight for sb in qir.store_bill_list if not sb.delivered) for qir in self.qir_list)

    @property
    def passed_weight(self):
        return sum(qir.weight for qir in self.qir_list if qir.result==constants.quality_inspection.FINISHED)

    @classmethod
    def new_work_command(cls, sub_order_id, org_weight, org_cnt, procedure_id,
                         urgent, tech_req="", pic_path=""):
        """

        :param cls:
        :param sub_order_id:
        :param org_weight:
        :param org_cnt:
        :param procedure_id:
        :param urgent:
        :param tech_req:
        :param pic_path:
        :return: 新生成的WorkCommandWrapper
        :raise: ValueError 如果参数错误
        """

        from litefac.apis import order

        try:
            sub_order = order.get_sub_order(sub_order_id).model
        except AttributeError:
            raise ValueError(_(u"没有该子订单%d" % sub_order_id))

        if not org_cnt:
            if sub_order.order_type == constants.EXTRA_ORDER_TYPE:
                raise ValueError(_(u"需要schedule_count字段"))
            else:
                org_cnt = org_weight

        if procedure_id:
            try:
                procedure = models.Procedure.query.filter(
                    models.Procedure.id == procedure_id).one()
            except NoResultFound:
                raise ValueError(_(u"没有该工序"))
        else:
            procedure = None

        if sub_order.remaining_quantity < org_cnt:
            raise ValueError(_(u"子订单的未排产数量小于%d" % org_cnt))
        org_weight = int(sub_order.unit_weight * org_cnt)

        work_command = models.WorkCommand(sub_order=sub_order,
                                          org_weight=org_weight,
                                          procedure=procedure,
                                          tech_req=tech_req,
                                          urgent=urgent, org_cnt=org_cnt,
                                          pic_path=pic_path or sub_order
                                          .pic_path)
        if sub_order.returned:
            work_command.processed_cnt = work_command.org_cnt
            work_command.processed_weight = work_command.org_weight
            work_command.status = constants.work_command\
            .STATUS_QUALITY_INSPECTING
        sub_order.remaining_quantity -= org_cnt

        do_commit([sub_order, work_command])

        return WorkCommandWrapper(work_command)

    @classmethod
    def get_list(cls, status_list, harbor=None, department_id=None,
                 normal=None, team_id=None, start=0, cnt=sys.maxint,
                 keywords=None, order_id=None, date=None):
        """get the work command list from database, sorted by last mod time
        descentally
        :param status_list: the status of to retrieve, should be a list of integers
        """
        import types

        wc_q = models.WorkCommand.query.join(models.SubOrder)

        if isinstance(status_list, types.ListType):
            wc_q = wc_q.filter(models.WorkCommand.status.in_(status_list))
        if department_id:
            wc_q = wc_q.filter(
                models.WorkCommand.department_id == department_id)
        if team_id:
            wc_q = wc_q.filter(models.WorkCommand.team_id == team_id)
        if harbor and harbor != u"全部":
            wc_q = wc_q.filter(
                models.SubOrder.harbor_name == harbor)
        if normal:
            wc_q = wc_q.filter(models.WorkCommand.org_weight > 0)
        if keywords:
            wc_q = wc_q.filter(
                models.WorkCommand.id.like("%" + keywords + "%"))
        if order_id:
            wc_q = wc_q.filter(models.WorkCommand.sub_order_id.in_(
                [sub_order.id for sub_order in models.SubOrder.query.filter(
                    models.SubOrder.order_id == order_id)]))
        if date:
            wc_q = wc_q.filter(models.WorkCommand.last_mod > date)
        total_cnt = wc_q.count()
        wc_q = wc_q.order_by(models.SubOrder.returned.desc()).order_by(
            models.WorkCommand.urgent.desc()).order_by(
            models.SubOrder.returned.desc()).order_by(
            models.WorkCommand.create_time.asc()).offset(start).limit(cnt)
        return [WorkCommandWrapper(wc) for wc in wc_q.all()], total_cnt

    @classmethod
    def get_work_command(cls, id_):
        """
        get work command from database
        :return: WorkCommandWrapper or None
        """
        if not id_:
            return None
        try:
            return WorkCommandWrapper(
                models.WorkCommand.query.filter(
                    models.WorkCommand.id == id_).one())
        except NoResultFound:
            return None


    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.model, k):
                setattr(self.model, k, v)
        do_commit(self.model)

    def go(self, actor_id, **kwargs):
        class _ValidationForm(Form):
            def add_value(self, **kwargs):
                try:
                    self.__values.update(kwargs)
                except AttributeError:
                    self.__values = {}
                    self.__values.update(kwargs)

            @property
            def values(self):
                try:
                    ret = self.__values
                except AttributeError:
                    ret = {}
                ret.update(self.data)
                # remove none values
                for k, v in ret.items():
                    if v is None:
                        ret.pop(k)
                return ret

            def validate_team_id(self, field): # pylint: disable=R0201
                if self.action.data == constants.work_command.ACT_ASSIGN:
                    if not field:
                        raise ValidationError("team_id required when "
                                              "assigning work command")
                    try:
                        self.add_value(
                            team=TeamWrapper.get_team(field.data).model)
                    except AttributeError:
                        raise ValidationError(
                            "no such team " + str(field.data))

            def validate_department_id(self, field):
                if self.action.data == constants.work_command.ACT_DISPATCH:
                    if not field:
                        raise ValidationError("department_id required when "
                                              "dispatching work command")
                    try:
                        self.add_value(
                            department=DepartmentWrapper.get_department(
                                field.data).model)
                    except AttributeError:
                        raise ValidationError(
                            "no such department " + str(field.data))

            valid_actions = [constants.work_command.ACT_DISPATCH,
                             constants.work_command.ACT_ASSIGN,
                             constants.work_command.ACT_ADD_WEIGHT,
                             constants.work_command.ACT_END,
                             constants.work_command.ACT_CARRY_FORWARD,
                             constants.work_command.ACT_RETRIEVAL,
                             constants.work_command.ACT_REFUSE,
                             constants.work_command.ACT_AFFIRM_RETRIEVAL,
                             constants.work_command.ACT_QI,
                             constants.work_command.ACT_REFUSE_RETRIEVAL,
                             constants.work_command.ACT_RETRIVE_QI,
                             constants.work_command.ACT_QUICK_CARRY_FORWARD]
            action = IntegerField("action", [validators.AnyOf(valid_actions)])
            team_id = IntegerField("team id")
            department_id = IntegerField("department id")
            quantity = IntegerField("quantity")
            weight = IntegerField("weight")
            tech_req = TextField("tech_req")
            urgent = BooleanField("urgent")
            deduction = IntegerField("deduction")
            procedure_id = IntegerField("procedure_id")



        form = _ValidationForm(MultiDict(kwargs))
        if not form.validate():
            raise ValueError(form.errors)
        from .work_command_state import work_command_sm
        if not work_command_sm.logger:
            from litefac.basemain import timeline_logger
            work_command_sm.logger = timeline_logger
        try:
            work_command_sm.reset_obj(work_command=self.model)
            d = form.values
            if 'qir_list' in kwargs:
                d.update([('qir_list', kwargs['qir_list'])])
            work_command_sm.next(actor=models.User.query.get(actor_id), **d)
        except Exception, e:
            raise ValueError(e.message)
        self.model.last_mod = datetime.now()
        do_commit(self.model)


    @property
    def retrievable(self):
        return self.status in [constants.work_command.STATUS_ASSIGNING,
                               constants.work_command.STATUS_ENDING]

    @property
    def deduction(self):
        return sum(deduction.weight for deduction in self.deduction_list)


    @property
    def action_list(self):
        if self.status == constants.work_command.STATUS_DISPATCHING:
            return [{"name": u"排产", "method": "GET",
                     "url": url_for("manufacture.schedule"),
                     "extra": {"work_command_id": self.id}}]
        elif self.status == constants.work_command.STATUS_ASSIGNING:
            return [{"name": u"回收", "method": "POST",
                     "url": url_for("manufacture.retrieve"),
                     "extra": {"work_command_id": self.id}}]

    @property
    def url(self):
        from litefac.permissions.work_command import view_work_command

        if view_work_command.can():
            return url_for("manufacture.work_command", id_=self.id,
                           url=request.url)
        else:
            return ""

    @property
    def log_list(self):
        from litefac.apis.log import LogWrapper

        ret = LogWrapper.get_log_list(str(self.id), self.model.__class__.__name__)
        return sorted(ret, lambda a, b: cmp(a.create_time, b.create_time), reverse=True)

    @property
    def cause(self):
        if self.previous_work_command:
            if not self.parent_qir:
                return constants.work_command.CAUSE_CARRY
            elif self.parent_qir.result == constants.quality_inspection.REPAIR:
                return constants.work_command.CAUSE_REPAIR
            elif self.parent_qir.result == constants.quality_inspection.REPLATE:
                return constants.work_command.CAUSE_REPLATE
            elif self.parent_qir.result == constants.quality_inspection.NEXT_PROCEDURE:
                return constants.work_command.CAUSE_NEXT
        return constants.work_command.CAUSE_NORMAL

    _cause_name = {constants.work_command.CAUSE_NORMAL: u"预排产", constants.work_command.CAUSE_NEXT: u"转下道工序",
                   constants.work_command.CAUSE_REPAIR: u"返修", constants.work_command.CAUSE_REPLATE: u"返镀",
                   constants.work_command.CAUSE_CARRY: u"结转"}

    @property
    def cause_name(self):
        return self._cause_name.get(self.cause, u"预排产")

class DepartmentWrapper(ModelWrapper):
    @classmethod
    def get_list(cls):
        return [DepartmentWrapper(d) for d in models.Department.query.all()]

    @classmethod
    def get_department(cls, id_):
        if not id_:
            return None
        try:
            return DepartmentWrapper(
                models.Department.query.filter(
                    models.Department.id == id_).one())
        except NoResultFound:
            return None


class TeamWrapper(ModelWrapper):
    @classmethod
    def get_list(cls, department_id=None):
        """
        get teams from database
        :rtype: ListType
        """
        query_ = models.Team.query
        if department_id:
            query_ = query_.filter(models.Team.department_id == department_id)
        return [TeamWrapper(team) for team in query_.all()]


    @classmethod
    def get_team(cls, id_):
        """
        get team from database according to id_
        :return TeamWrapper or None
        """
        if not id_:
            return None
        try:
            return TeamWrapper(models.Team.query.filter(
                models.Team.id == id_).one())
        except NoResultFound:
            return None

    def get_team_work_command_dict(self, begin_date=None, end_date=None):
        #只计算生产完毕的
        wc_dict = {}
        for wc in get_work_command_list(
            status_list=[constants.work_command.STATUS_FINISHED],
            team_id=self.id)[0]:
            list_ = wc_dict.setdefault(wc.create_time.strftime("%Y-%m-%d"), [])
            flag = True
            if begin_date:
                flag = flag and (wc.create_time.date() >= begin_date.date())
            if end_date:
                flag = flag and (wc.create_time.date() <= end_date.date())
            if flag and wc.org_weight > 0:
                list_.append(wc)
        return wc_dict


def get_status_list():
    return [
        ((constants.work_command.STATUS_DISPATCHING, constants.work_command.STATUS_REFUSED), u'待生产', u"需要调度员排产的工单"),
        ((constants.work_command.STATUS_ENDING, constants.work_command.STATUS_ASSIGNING,
          constants.work_command.STATUS_LOCKED), u'生产中', u"进入生产环节的工单"),
        (constants.work_command.STATUS_QUALITY_INSPECTING, u'待质检',
         u"待质检员质检完成的工单"),
        (constants.work_command.STATUS_FINISHED, u'已完成', u"已经结束生产的工单"),
    ]


def get_wc_status_list():
    return {
        constants.work_command.STATUS_DISPATCHING: (u'待排产', u'待调度员排产'),
        constants.work_command.STATUS_ASSIGNING: ( u'待分配', u'待车间主任分配'),
        constants.work_command.STATUS_LOCKED: (u'锁定', u'调度员已请求回收，待车间主任处理'),
        constants.work_command.STATUS_ENDING: (u'待请求结转或结束', u'待班组长结转或结束'),
        constants.work_command.STATUS_QUALITY_INSPECTING: (
            u'待质检', u'待质检员质检完成'),
        constants.work_command.STATUS_REFUSED: (u'车间主任打回', u'调度员分配后，被车间主任打回'),
        constants.work_command.STATUS_FINISHED: (u'已结束', u'已经结束生产'),
    }


def get_handle_type_list():
    return {
        constants.work_command.HT_NORMAL: u'正常加工',
        constants.work_command.HT_REPAIRE: u'返修',
        constants.work_command.HT_REPLATE: u'返镀'
    }


get_work_command_list = WorkCommandWrapper.get_list
get_work_command = WorkCommandWrapper.get_work_command
new_work_command = WorkCommandWrapper.new_work_command
get_team_list = TeamWrapper.get_list
get_team = TeamWrapper.get_team
get_department_list = DepartmentWrapper.get_list
get_department = DepartmentWrapper.get_department
