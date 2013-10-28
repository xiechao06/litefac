# -*- coding: UTF-8 -*-
import types

_wrappers = {}


class ModelWrapper(object):
    def __init__(self, model):
        self.__model = model

    @property
    def model(self):
        return self.__model

    def __getattr__(self, name):
        unwrapped = False
        if name.endswith("unwrapped"):
            name = name[0:-len("_unwrapped")]
            unwrapped = True
            attr = getattr(self, name)
        else:
            attr = getattr(self.__model, name)
        if isinstance(attr, types.ListType) or isinstance(attr,
                                                          types.TupleType):
            if unwrapped:
                return type(attr)(self.__unwrap(i) for i in attr)
            else:
                return type(attr)(self.__wrap(i) for i in attr)
        return attr if unwrapped else self.__wrap(attr)

    def __setattr__(self, key, value):
        if key != '_ModelWrapper__model':
            self.__model.__setattr__(key, value)
        else:
            self.__dict__[key] = value

    def __wrap(self, attr):
        from litefac.database import db

        if isinstance(attr, db.Model):
            return self.__do_wrap(attr)
        return attr

    def __unwrap(self, attr):

        if isinstance(attr, ModelWrapper):
            return attr.model
        return attr

    def __do_wrap(self, attr):
        try:
            return _wrappers[attr.__class__.__name__ + "Wrapper"](attr)
        except KeyError:
            return attr

    def __unicode__(self):
        return unicode(self.model)

    def __dir__(self):
        return self.model.__dict__.keys()


def wraps(model):
    try:
        return _wrappers[model.__class__.__name__ + "Wrapper"](model)
    except KeyError:
        return model


import auth
import cargo
import customer
import order
import manufacture
import quality_inspection
import delivery
import product
import store
import harbor
import broker
import plate
import log
import config
import todo

from path import path

for fname in path(__path__[0]).files("[!_]*.py"):
    fname = fname.basename()[:-len(".py")]
    package = __import__(str("litefac.apis." + fname), fromlist=[str(fname)])
    for k, v in package.__dict__.items():
        if isinstance(v, types.TypeType) and \
                issubclass(v, ModelWrapper) and \
                k.endswith("Wrapper"):
            _wrappers[k] = v
            globals()[k] = v # install all the wrappers in this module

