# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
与MSSQL交互
"""


import httplib
import json
from litefac.basemain import app

def get_connection():
    return httplib.HTTPConnection(app.config["BROKER_IP"],
                                app.config["BROKER_PORT"],
                                timeout=app.config["BROKER_TIMEOUT"])

def _get_data_from_remote(data_type):
    connection = get_connection()
    connection.request("GET", "/" + data_type)
    rv = connection.getresponse()
    if rv.status != 200:
        raise ValueError(rv.read())
    obj = json.loads(rv.read())
    return obj

def import_products():
    return _get_data_from_remote("products")


def import_types():
    return _get_data_from_remote("product-types")

def import_customers():
    return _get_data_from_remote("customers")

def import_consignments():
    return _get_data_from_remote("consignments")


def export_consignment(consignment):
    def consignment2dict(consignment):
        _dic = {"consignment_id": consignment.consignment_id,
                "customer_id": consignment.customer.MSSQL_ID,
                "plate": consignment.delivery_session.plate,
                "weight": sum(product.weight for product in consignment.product_list),
                "quantity": sum(product.quantity for product in consignment.product_list),
                "product_list": [{"id": p.product.MSSQL_ID,
                                  "name": p.product.name,
                                  "quantity": p.quantity,
                                  "weight": p.weight,
                                  "isReturned":1 if p.returned_weight else 0} for p in
                                 consignment.product_list]}
        return _dic
    connection = get_connection()
    connection.request("POST", "/consignments", json.dumps(consignment2dict(consignment)))
    rv = connection.getresponse()
    if rv.status != 200:
        raise ValueError(rv.read())
    return rv.read()
