# -*- coding: utf-8 -*-
import os
import types
import time
from datetime import datetime

#from tornado import locale
#user_locale = locale.get(app.config["LOCALE"])
#_ = user_locale.translate
# TODO do translate in future
_ = lambda x, **kwargs: x


def dictview(fields, d):
    items = []
    for field in fields:
        if isinstance(field, types.StringType):
            items.append((field, d.get(field)))
        elif isinstance(field, types.TupleType):
            items.append((field[0], d.get(field[1])))
    return dict(items)


def convert_time(d):
    for k, v in d.items():
        if k == u"due_time":
            d[k] = datetime.strptime(v, '%Y-%m-%d')
        if k == u"finish_time":
            d[k] = datetime.strptime(v, '%Y-%m-%d %H:%M:%S')


def find_first(iterable, f):
    return ([o for o in iterable if f(o)] or [None])[0]


def to_timestamp(dt):
    if isinstance(dt, datetime):
        return int(time.mktime(dt.timetuple()))
    elif isinstance(dt, time.struct_time):
        return int(time.mktime(dt))
    elif not dt:
        return None
    else:
        raise ValueError("%s can't convert to timestamp" % str(dt))


def action_name(action):
    from litefac.constants import work_command

    if action == work_command.ACT_CHECK:
        return _(u"<检货>")
    elif action == work_command.ACT_DISPATCH:
        return _(u"<排产>")
    elif action == work_command.ACT_ASSIGN:
        return _(u"<分配>")
    elif action == work_command.ACT_ADD_WEIGHT:
        return _(u"<增加重量>")
    elif action == work_command.ACT_END:
        return _(u"<请求结束>")
    elif action == work_command.ACT_CARRY_FORWARD:
        return _(u"<请求结转>")
    elif action == work_command.ACT_REFUSE:
        return _(u"<打回工单>")
    elif action == work_command.ACT_RETRIEVAL:
        return _(u"<回收>")
    elif action == work_command.ACT_AFFIRM_RETRIEVAL:
        return _(u"<确认回收>")
    elif action == work_command.ACT_QI:
        return _(u"<质检>")
    elif action == work_command.ACT_QUICK_CARRY_FORWARD:
        return _(u"<快速结转>")
    elif action == work_command.ACT_RETRIVE_QI:
        return _(u"<取消质检报告>")
    elif action == work_command.ACT_REFUSE_RETRIEVAL:
        return _(u"<拒绝回收>")
    else:
        return _(u"<未知>")


def status_name(status):
    from litefac.constants import work_command

    if status == work_command.STATUS_DISPATCHING:
        return _(u"<待排产>")
    elif status == work_command.STATUS_ASSIGNING:
        return _(u"<待分配>")
    elif status == work_command.STATUS_LOCKED:
        return _(u"<锁定， 待车间主任确认回收>")
    elif status == work_command.STATUS_ENDING:
        return _(u"<待请求结转或结束>")
    elif status == work_command.STATUS_QUALITY_INSPECTING:
        return _(u"<待质检>")
    elif status == work_command.STATUS_REFUSED:
        return _(u"<车间主任打回>")
    elif status == work_command.STATUS_FINISHED:
        return _(u"<已经结束>")


def repr_wtforms_error(errors):
    return ";".join("%s: %s" % (k, ",".join(v)) for k, v in errors.items())


def fslice(iterable, predict):
    a = []
    b = []
    for i in iterable:
        if predict(i):
            a.append(i)
        else:
            b.append(i)
    return a, b


class Config(object):
    __instance__ = None

    @classmethod
    def instance(cls):
        if cls.__instance__ is None:
            cls.__instance__ = Config()
        return cls.__instance__

    def __init__(self):
        import litefac.default_settings as config1

        self.config1 = config1
        try:
            if 'LITE_MMS_HOME' in os.environ:
                os.chdir(os.environ["LITE_MMS_HOME"])
                from litefac import config

                self.config2 = config.__dict__
            else:
                self.config2 = {}
        except ImportError:
            self.config2 = {}
        import types

        d = types.ModuleType('config3')
        d.__file__ = "config.py"
        try:
            execfile("config.py", d.__dict__)
            self.config3 = d
        except IOError:
            self.config3 = {}

    def __getattr__(self, name):
        try:
            return getattr(self.config3, name)
        except AttributeError:
            pass
        try:
            return getattr(self.config2, name)
        except AttributeError:
            pass
        try:
            return getattr(self.config1, name)
        except AttributeError:
            raise AttributeError("no such option: " + name)


def do_commit(obj, action="add"):
    from litefac.database import db

    if action == "add":
        if isinstance(obj, types.ListType) or isinstance(obj, types.TupleType):
            db.session.add_all(obj)
        else:
            db.session.add(obj)
    elif action == "delete":
        db.session.delete(obj)
    db.session.commit()
    return obj


def check_raise(obj, f, ExceptionCls, msg=u""):
    if f(obj):
        raise ExceptionCls(msg)
    return obj


def get_or_404(cls, id_):
    from litefac.database import db
    from litefac.apis import ModelWrapper, wraps

    assert issubclass(cls, db.Model) or issubclass(cls, ModelWrapper)

    return wraps(cls.query.get_or_404(id_))


def _seek(seq, idfun):
    seen = set()
    if idfun is None:
        idfun = lambda x: x
    for x in seq:
        try:
            x_ = idfun(x)
        except:
            continue
        if x_ in seen:
            continue
        seen.add(x_)
        yield x


def deduplicate(seq, idfun=None):
    return list(_seek(seq=seq, idfun=idfun))


def camel_case(str_):
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', str_)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def gen_qir_pic_path(idx):
    return 'qir-' + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '_' + \
        str(idx) + ".jpeg"
