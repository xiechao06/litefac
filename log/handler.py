#-*- coding:utf-8 -*-
from datetime import datetime
import logging
from litefac.models import Log
from litefac.utilities import do_commit
from litefac.apis import ModelWrapper


class DBHandler(logging.Handler):
    """
    Handler for logging message to the database table "log"
    """

    def emit(self, record):
        log = Log()
        obj = getattr(record, "obj", None)
        if obj:
            log.obj = unicode(obj)
        obj_cls = getattr(record, "obj_cls", None)
        if obj_cls:
            log.obj_cls = obj_cls
        else:
            if obj:
                if isinstance(obj, ModelWrapper):
                    log.obj_cls = obj.model.__class__.__name__
                else:
                    log.obj_cls = obj.__class__.__name__
        obj_pk = getattr(record, "obj_pk", None)
        if obj_pk:
            log.obj_pk = obj_pk
        log.actor = getattr(record, "actor", None)
        log.action = getattr(record, "action", "")
        log.create_time = datetime.now()
        log.message = record.msg[:Log.message.property.columns[0].type.length]
        #log.name = record.name
        #log.level = record.levelname
        #log.module = record.module
        #log.func_name = record.funcName
        #log.line_no = record.lineno
        #log.thread = record.thread
        #log.thread_name = record.threadName
        #log.process = record.process
        #log.args = str(record.args)
        do_commit(log)
