# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
from sqlalchemy.exc import SQLAlchemyError
from litefac import models

def get_harbor_list(department_id=None):
    query_ = models.Harbor.query
    if department_id:
        query_ = query_.filter(models.Harbor.department_id==department_id)
    return query_.all()

def get_harbor_model(name):
    if not name:
        return None
    try:
        return models.Harbor.query.filter(
            models.Harbor.name == name).one()
    except:
        return None
