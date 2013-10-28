#-*- coding:utf-8 -*-
from flask.ext.databrowser import action
from flask import redirect, url_for, request
from flask.ext.login import current_user
from litefac import constants
from litefac.apis import wraps


class ScheduleAction(action.DirectAction):

    def op_upon_list(self, objs, model_view):
        return redirect(
            url_for("manufacture.schedule", _method="GET", work_command_id=[obj.id for obj in objs], url=request.url))

    def test_enabled(self, model):
        if model.status in (constants.work_command.STATUS_DISPATCHING, constants.work_command.STATUS_REFUSED):
            return 0
        else:
            return -2

    def _get_forbidden_msg_formats(self):
        return {-2: u"只有状态为待排产或者车间主任打回的工单才能排产"}


class RetrieveAction(action.BaseAction):

    def op(self, obj):
        wraps(obj).go(actor_id=current_user.id, action=constants.work_command.ACT_RETRIEVAL)

    def test_enabled(self, model):
        if model.status in (constants.work_command.STATUS_ASSIGNING, constants.work_command.STATUS_ENDING):
            return 0
        else:
            return -2

    def _get_forbidden_msg_formats(self):
        return {-2: u"状态不符合"}


schedule_action = ScheduleAction(u"排产")

retrieve_action = RetrieveAction(u"回收")
