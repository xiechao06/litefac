# -*- coding: utf-8 -*-
from lite_sm import StateMachine, State, RuleSpecState, InvalidAction
from litefac.constants import cargo as cargo_const
from litefac.permissions.roles import CargoClerkPermission
from litefac.utilities.decorators import committed
from litefac.basemain import timeline_logger

class UnloadSessionFSM(StateMachine):

    def reset_obj(self, obj):
        if obj.status == cargo_const.STATUS_LOADING:
            self.set_current_state(state_loading)
        elif obj.status == cargo_const.STATUS_WEIGHING:
            self.set_current_state(state_weighing)
        elif obj.status == cargo_const.STATUS_CLOSED:
            self.set_current_state(state_closed)
        self.obj = obj

    def do_log(self, action, actor):
        #msg = u"用户(%s)对卸货会话%s执行了%s操作，卸货会话的状态从(%s)转变为(%s)" % (actor.username, self.obj, cargo_const.desc_action(action), self.last_state, self.current_state)
        msg = ""
        self.logger.info(msg, extra={"obj": self.obj.model, "actor": actor, "action": cargo_const.desc_action(action), "obj_pk": self.obj.id})

fsm = UnloadSessionFSM(logger=timeline_logger)

class StateLoading(RuleSpecState):
    status = cargo_const.STATUS_LOADING

    def __unicode__(self):
        return u"正在卸载"
    
    @committed
    def side_effect(self, **kwargs):
        self.obj.status = cargo_const.STATUS_LOADING
        self.obj.finish_time = None
        return self.obj.model

state_loading = StateLoading(fsm, {
    cargo_const.ACT_LOAD: (cargo_const.STATUS_WEIGHING, None),
    cargo_const.ACT_CLOSE: (cargo_const.STATUS_CLOSED, None)
})

class StateWeighing(State):
    status = cargo_const.STATUS_WEIGHING

    def __unicode__(self):
        return u"等待称重"

    @committed
    def side_effect(self, **kwargs):
        self.obj.status = cargo_const.STATUS_WEIGHING 
        return self.obj.model

    def next(self, action):
        CargoClerkPermission.test()
        if action == cargo_const.ACT_WEIGHT:
            if self.obj.task_list and self.obj.task_list[-1].is_last:
                return state_closed
            return state_loading
        else:
            raise InvalidAction(fsm.invalid_info(action, self))

state_weighing = StateWeighing(fsm)

class StateClosed(RuleSpecState):
    status = cargo_const.STATUS_CLOSED

    def __unicode__(self):
        return u"关闭"

    @committed
    def side_effect(self, **kwargs):
        CargoClerkPermission.test()
        self.obj.status = cargo_const.STATUS_CLOSED
        from datetime import datetime
        self.obj.finish_time = datetime.now()
        return self.obj.model

state_closed = StateClosed(fsm, {
    cargo_const.ACT_OPEN: (cargo_const.STATUS_LOADING, CargoClerkPermission)
})

