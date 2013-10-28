class State:
    @property
    def last_status(self):
        return self.last_state.status

    def run(self):
        assert 0, "run not implemented"

    def next(self, input):
        assert 0, "next not implemented"


class StateMachine(object):
    def __init__(self, init_state, logger=None):
        self.current_state = init_state
        self.current_state.sm = self
        self.logger = logger

    def next(self, action, *args, **kwargs):
        last_state = self.current_state
        self.current_state = last_state.next(action)
        self.current_state.last_state = last_state
        self.current_state.action = action
        self.current_state.sm = self
        self.current_state.run(*args, **kwargs)
        if self.logger:
            self.do_log(action, *args, **kwargs)

    def do_log(self, action, *args, **kwargs):
        self.logger.info(u"action:%s" % action, *args, **kwargs)