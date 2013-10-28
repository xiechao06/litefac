#-*- coding:utf-8 -*-
from lite_sm import StateMachine, RuleSpecState, State, InvalidAction
from litefac.basemain import timeline_logger
from litefac.constants import delivery
from litefac.permissions import CargoClerkPermission
from litefac.utilities.decorators import committed


class DeliverySessionFSM(StateMachine):
    def reset_obj(self, obj):
        if obj.status == delivery.STATUS_LOADING:
            self.set_current_state(state_loading)
        elif obj.status == delivery.STATUS_WEIGHING:
            self.set_current_state(state_weighing)
        elif obj.status == delivery.STATUS_CLOSED:
            self.set_current_state(state_closed)
        self.obj = obj

    def do_log(self, action, actor):
        msg = ""
        self.logger.info(msg, extra={"obj": self.obj.model, "actor": actor, "action": delivery.desc_action(action),
                                     "obj_pk": self.obj.id})


fsm = DeliverySessionFSM(logger=timeline_logger)


class StateLoading(RuleSpecState):
    status = delivery.STATUS_LOADING

    def __unicode__(self):
        return u"正在装货"

    @committed
    def side_effect(self, **kwargs):
        self.obj.status = delivery.STATUS_LOADING
        self.obj.finish_time = None
        return self.obj.model


state_loading = StateLoading(fsm, {
    delivery.ACT_LOAD: (delivery.STATUS_WEIGHING, None),
    delivery.ACT_CLOSE: (delivery.STATUS_CLOSED, None)
})


class StateWeighing(State):
    status = delivery.STATUS_WEIGHING

    def __unicode__(self):
        return u"等待称重"

    @committed
    def side_effect(self, **kwargs):
        self.obj.status = delivery.STATUS_WEIGHING
        return self.obj.model

    def next(self, action):
        CargoClerkPermission.test()
        if action == delivery.ACT_WEIGHT:
            if self.obj.delivery_task_list[-1].is_last:
                return state_closed
            return state_loading
        else:
            raise InvalidAction(fsm.invalid_info(action, self))


state_weighing = StateWeighing(fsm)


class StateClosed(RuleSpecState):
    status = delivery.STATUS_CLOSED

    def __unicode__(self):
        return u"关闭"

    @committed
    def side_effect(self, **kwargs):
        CargoClerkPermission.test()
        for sb in self.obj.store_bill_list:
            if sb.delivery_session and sb.delivery_task is None:
                sb.delivery_session = None

        self.obj.status = delivery.STATUS_CLOSED
        from datetime import datetime

        self.obj.finish_time = datetime.now()
        return self.obj.model


state_closed = StateClosed(fsm, {
    delivery.ACT_OPEN: (delivery.STATUS_LOADING, CargoClerkPermission)
})

