# -*- coding:UTF-8 -*-
from sqlalchemy.orm.exc import NoResultFound
from litefac import models
from litefac.apis import ModelWrapper
from litefac.utilities import do_commit

class CustomerWrapper(ModelWrapper):
    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, CustomerWrapper) and other.id == self.id

    def __hash__(self):
        return hash(self.id)

    @classmethod
    def get_list(cls):
        """
        get customer list from database
        """
        return [CustomerWrapper(c) for c in models.Customer.query.all()]


    @classmethod
    def get_customer(cls, customer_id):
        """
        get a customer by id from database
        :return: the customer of given id or None if there's no such customer
        """
        if  not customer_id:
            return None
        try:
            return CustomerWrapper(models.Customer.query.filter(
                models.Customer.id == customer_id).one())
        except NoResultFound:
            return None

    @classmethod
    def get_customer_list(cls, model):
        q = models.Customer.query
        if model:
            q = q.join(model).filter(model.customer != None)
        return [CustomerWrapper(customer) for customer in q.all()]

def post_customers(data):
    count = 0
    for customer in data:
        try:
            models.Customer.query.filter(
                models.Customer.name == customer["name"]).one()
        except NoResultFound:
            do_commit(models.Customer(name=customer["name"],
                                      abbr=customer["short"],
                                      MSSQL_ID=customer["id"]))
            count += 1
    return u"成功添加%d条客户信息" % count

get_customer_list = CustomerWrapper.get_list
get_customer = CustomerWrapper.get_customer
