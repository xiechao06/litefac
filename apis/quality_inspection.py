# -*- coding: UTF-8 -*-
import sys
from flask import url_for
from litefac.utilities import _
from sqlalchemy.orm.exc import NoResultFound
from litefac import models
from litefac.constants import (work_command as wc_const,
                                quality_inspection as qi_const)
from litefac.apis import ModelWrapper
from litefac.utilities import do_commit


class QIReportWrapper(ModelWrapper):
    @property
    def pic_url(self):
        if self.pic_path:
            return url_for("serv_pic", filename=self.pic_path)
        else:
            return ""

    @property
    def small_pic_url(self):
        return url_for("serv_small_pic", filename=self.pic_path) if self.pic_path else ""

    @property
    def reporter(self):
        return self.actor

    @property
    def partly_delivered(self):
        """
        若有对应的仓单正在被装货，或已经发货， 就认为这个质检报告部分已经被发货
        """
        return any(sb.delivery_session for sb in self.store_bill_list)

    @classmethod
    def get(cls, id_):
        if not id_:
            return None
        try:
            return QIReportWrapper(
                models.QIReport.query.filter_by(id=id_).one())
        except NoResultFound:
            return None

    @classmethod
    def new(cls, actor_id, work_command_id, quantity, result, pic_path,
            report_time=None):
        from litefac.apis.manufacture import WorkCommandWrapper

        workcommand = WorkCommandWrapper.get_work_command(
            work_command_id)
        if not workcommand:
            raise ValueError(_(u"无该工单%s" % work_command_id))
        weight = workcommand.model.processed_unit_weight * quantity
        qi_report = models.QIReport(workcommand.model, quantity, weight,
                                    result, actor_id, report_time, pic_path)
        return QIReportWrapper(do_commit(qi_report))

    @classmethod
    def remove(cls, id_, actor_id):
        """
        remove the quality inspection report on database
        """
        qir = cls.get(id_)
        if not qir:
            raise ValueError(_(u"无此报告单(%s)" % id_))
        if qir.work_command.status != wc_const.STATUS_QUALITY_INSPECTING:
            raise ValueError(_(u"已提交的质检单中的质检报告不能删除"))
        do_commit(qir.model, action="delete")
        return "sucess"

    @classmethod
    def update(cls, id_, actor_id, quantity=None, result=None, pic_path=None):
        """
        update quality inspection report in database
        """
        qir = cls.get(id_)
        if not qir:
            raise ValueError(_(u"无此报告%s" % id_))
        if quantity:
            qir.model.quantity = quantity
        if result is not None:
            qir.model.result = result
        if pic_path:
            qir.model.pic_path = pic_path
        qir.model.actor_id = actor_id
        return QIReportWrapper(do_commit(qir.model))

    @property
    def product(self):
        return self.work_command.sub_order.product

    @property
    def unit(self):
        return self.work_command.sub_order.unit


def get_qir_list(work_command_id=None, idx=0, cnt=sys.maxint,
                 finished_only=False, result=None):
    """
    get the quality inspection_report from database
    """
    qir_q = models.QIReport.query
    if work_command_id:
        qir_q = qir_q.filter(models.QIReport.work_command_id ==
                             work_command_id)
    if finished_only:
        # see sqlalchemy IS NULL
        qir_q = qir_q.filter(models.QIReport.report_time == None)
    if result:
        qir_q = qir_q.filter(models.QIReport.result == result)

    total_cnt = qir_q.count()
    qir_q = qir_q.offset(idx).limit(cnt)
    return [QIReportWrapper(qir) for qir in qir_q.all()], total_cnt

get_qir = QIReportWrapper.get
new_QI_report = QIReportWrapper.new
remove_qi_report = QIReportWrapper.remove
update_qi_report = QIReportWrapper.update


def get_QI_result_list():
    return [
        (qi_const.FINISHED, u'通过'),
        (qi_const.NEXT_PROCEDURE, u'通过转下道工序'),
        (qi_const.REPAIR, u'返修'),
        (qi_const.REPLATE, u'返镀'),
        (qi_const.DISCARD, u'报废'),
    ]
