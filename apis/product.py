# -*- coding:UTF-8 -*-
from sqlalchemy.orm.exc import NoResultFound
from litefac import models
from litefac.utilities import do_commit

def get_product_types():
    """
    get the product types
    :return a list of dict, each dict has keys "id", "name"
    """
    return [dict(id=t.id, name=t.name, MSSQL_ID=t.MSSQL_ID) for t in
            models.ProductType.query.all()]


def get_product_type(id_):
    """
    get the product types
    :return a list of dict, each dict has keys "id", "name"
    """
    if not id_:
        raise ValueError(u"产品类型ID不能为空")
    t = models.ProductType.query.filter(models.ProductType.id == id_).one()
    return dict(id=t.id, name=t.name, MSSQL_ID=t.MSSQL_ID)


def post_types(data):
    count = 0
    for type in data:
        try:
            models.ProductType.query.filter(
                models.ProductType.name == type["name"]).one()
        except NoResultFound:
            do_commit(
                models.ProductType(name=type["name"], MSSQL_ID=type["id"]))
            count += 1
    return u"成功添加%d条产品类型信息" % count


def get_products():
    """
    get the products
    :return a dict, the keys are product type id, the values are a list of 
    dict, each dict has keys "id", "name". for example:
    {
        '1': [{"id": 1, "name": "product a"}, {"id": 2, "name": "product b"}],
        '2': [{"id": 3, "name": "product c"}],
    }
    """
    products = models.Product.query.filter(models.Product.enabled==True).all()
    ret = {}
    for p in products:
        ret.setdefault(str(p.product_type_id), []).append(
            dict(id=p.id, name=p.name, MSSQL_ID=p.MSSQL_ID))
    return ret


def get_product(**kwargs):
    """
    :return the model of product
    """
    try:
        query_ = models.Product.query
        for k, v in kwargs.items():
            if not hasattr(models.Product, k):
                return None
            query_ = query_.filter(getattr(models.Product, k) == v)
        return query_.one()
    except NoResultFound:
        return None


def post_product(data):
    count = 0
    for k, v in data.items():
        product_type = models.ProductType.query.filter(
            models.ProductType.MSSQL_ID == int(k)).one()
        for product in v:
            try:
                models.Product.query.filter(
                    models.Product.name == product["name"]).filter(
                    models.Product.product_type == product_type).one()
            except NoResultFound:
                do_commit(models.Product(product["name"], product_type,
                                         MSSQL_ID=product["id"]))
                count += 1
    return u"成功添加%d条产品信息" % count



