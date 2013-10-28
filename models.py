# -*- coding: utf-8 -*-

from datetime import datetime

import flask.ext.databrowser as databrowser
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.properties import ColumnProperty

from litefac import constants
from litefac.database import db

permission_and_group_table = db.Table("TB_PERMISSION_AND_GROUP",
                                      db.Column("permission_name",
                                                db.String(64),
                                                db.ForeignKey(
                                                    'TB_PERMISSION.name')),
                                      db.Column("group_id", db.Integer,
                                                db.ForeignKey("TB_GROUP.id")))

user_and_group_table = db.Table('TB_ASSOCIATION',
                                db.Column('user_id', db.Integer,
                                          db.ForeignKey('TB_USER.id')),
                                db.Column('group_id', db.Integer,
                                          db.ForeignKey('TB_GROUP.id')))

department_and_user_table = db.Table("TB_DEPARTMENT_AND_USER",
                                     db.Column("department_id", db.Integer,
                                               db.ForeignKey(
                                                   'TB_DEPARTMENT.id')),
                                     db.Column("user_id", db.Integer,
                                               db.ForeignKey('TB_USER.id')))

procedure_and_department_table = db.Table("TB_PROCEDURE_AND_DEPARTMENT",
                                          db.Column("procedure_id", db.Integer,
                                                    db.ForeignKey(
                                                        "TB_PROCEDURE.id")),
                                          db.Column("department_id",
                                                    db.Integer,
                                                    db.ForeignKey(
                                                        "TB_DEPARTMENT.id")))

user_and_team_table = db.Table("TB_USER_AND_TEAM", db.Column("team_id", db.Integer, db.ForeignKey("TB_TEAM.id")),
                               db.Column("leader_id", db.Integer, db.ForeignKey("TB_USER.id")))
class _ResyncMixin(object):



    def resync(self):

        pk = databrowser.utils.get_primary_key(self.__class__)
        fresh_obj = self.query.filter(getattr(self.__class__, pk)==getattr(self, pk)).one()
        props = self.__class__._sa_class_manager.mapper.iterate_properties

        for p in props:
            if isinstance(p, ColumnProperty) and not p.is_primary:
                setattr(self, p.key, getattr(fresh_obj, p.key))
        return self



class Permission(db.Model):
    __tablename__ = "TB_PERMISSION"
    __modelname__ = u"权限"
    name = db.Column(db.String(64), primary_key=True)
    desc = db.Column(db.String(64), default="")

    def __unicode__(self):
        return self.name + '(' + self.desc + ')'

    def __repr__(self):
        return "<Permission: %s>" % self.name.encode("utf-8")


class Group(db.Model):
    __tablename__ = "TB_GROUP"
    __modelname__ = u"用户组"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    permissions = db.relationship("Permission",
                                  secondary=permission_and_group_table)
    default_url = db.Column(db.String(256))

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<Group: %d>" % self.id


class User(db.Model):
    __tablename__ = "TB_USER"
    __modelname__ = u"用户"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False, doc=u"这里保存的是密码明文的MD5值")
    groups = db.relationship("Group", secondary=user_and_group_table,
                             backref="users")
    tag = db.Column(db.String(32), nullable=True)
    enabled = db.Column(db.Boolean, default=True)

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return "<User %d>" % self.id

class UnloadSession(db.Model):
    __modelname__ = u"卸货会话"
    __tablename__ = "TB_UNLOAD_SESSION"

    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(32), db.ForeignKey('TB_PLATE.name'), nullable=False)
    plate_ = db.relationship("Plate")
    gross_weight = db.Column(db.Integer, nullable=False)
    with_person = db.Column(db.Boolean, default=False)
    status = db.Column(db.Integer, default=constants.cargo.STATUS_LOADING, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now)
    finish_time = db.Column(db.DateTime)
    goods_receipt_list = db.relationship(
        "GoodsReceipt", backref="unload_session",
        cascade="all, delete-orphan"
    )

    def __unicode__(self):
        return self.plate

    def __repr__(self):
        return "<UnloadSession %d>" % self.id

class UnloadTask(db.Model):
    __modelname__ = u"卸货任务"
    __tablename__ = "TB_UNLOAD_TASK"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('TB_UNLOAD_SESSION.id'))
    unload_session = db.relationship("UnloadSession", backref=db.backref("task_list", cascade="all, delete-orphan"))
    harbor_name = db.Column(db.String(32), db.ForeignKey('TB_HABOR.name'))
    harbor = db.relationship("Harbor")
    customer_id = db.Column(db.Integer, db.ForeignKey('TB_CUSTOMER.id'))
    customer = db.relationship("Customer")
    creator_id = db.Column(db.Integer, db.ForeignKey('TB_USER.id'))
    creator = db.relationship("User")
    pic_path = db.Column(db.String(256))
    create_time = db.Column(db.DateTime, default=datetime.now)
    weight = db.Column(db.Integer, default=0)
    product_id = db.Column(db.Integer, db.ForeignKey("TB_PRODUCT.id"))
    product = db.relationship("Product")
    is_last = db.Column(db.Boolean, default=False)

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<UnloadTask %d>" % self.id


class Customer(db.Model):
    __modelname__ = u"客户"
    __tablename__ = "TB_CUSTOMER"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    abbr = db.Column(db.String(32))
    enabled = db.Column(db.Boolean, default=True)
    MSSQL_ID = db.Column(db.Integer, default=0, nullable=False)


    def __init__(self, name, abbr, MSSQL_ID=0):
        self.name = name
        self.abbr = abbr
        self.MSSQL_ID = MSSQL_ID

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<Customer %s>" % self.id


class Harbor(db.Model):
    __modelname__ = u"装卸点"
    __tablename__ = "TB_HABOR"
    name = db.Column(db.String(32), nullable=False, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("TB_DEPARTMENT.id"))
    department = db.relationship("Department", backref="harbor_list", doc=u"装卸点卸载的待加工件将默认分配给此车间")


    def __unicode__(self):
        return unicode(self.name)

    def __repr__(self):
        return "<Harbor %s>" % self.name


class ProductType(db.Model):
    __modelname__ = u"产品类型"
    __tablename__ = "TB_PRODUCT_TYPE"
    id = db.Column(db.Integer, primary_key=True)
    MSSQL_ID = db.Column(db.Integer, default=0, nullable=True)
    name = db.Column(db.String(32), unique=True)

    def __init__(self, name, MSSQL_ID=0):
        self.name = name
        self.MSSQL_ID = MSSQL_ID

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<ProductType: %d>" % self.id


class Product(db.Model):
    __modelname__ = u"产品"
    __tablename__ = "TB_PRODUCT"
    id = db.Column(db.Integer, primary_key=True)
    MSSQL_ID = db.Column(db.Integer, default=0, nullable=True)
    name = db.Column(db.String(32))
    product_type_id = db.Column(db.Integer,
                                db.ForeignKey("TB_PRODUCT_TYPE.id"))
    product_type = db.relationship("ProductType", backref="products")
    enabled = db.Column(db.Boolean, default=True)

    def __init__(self, name, product_type, MSSQL_ID=0):
        self.name = name
        self.product_type = product_type
        self.MSSQL_ID = MSSQL_ID

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<Product %d>" % self.id


class Department(db.Model):
    __modelname__ = u"车间"
    __tablename__ = "TB_DEPARTMENT"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    team_list = db.relationship("Team", backref="department")
    leader_list = db.relationship("User", secondary=department_and_user_table,
                                  backref="department_list")


    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<Department %d>" % self.id

class Team(db.Model):
    __modelname__ = u"班组"
    __tablename__ = "TB_TEAM"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey('TB_DEPARTMENT.id'), nullable=False)
    leader_list = db.relationship("User", secondary=user_and_team_table, backref="team_list")

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<Team %s>" % self.id

class GoodsReceipt(db.Model):
    __modelname__ = u"收货单"
    __tablename__ = "TB_GOODS_RECEIPT"

    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.String(15), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('TB_CUSTOMER.id'))
    customer = db.relationship(Customer)
    unload_session_id = db.Column(db.Integer,
                                  db.ForeignKey('TB_UNLOAD_SESSION.id'))
    create_time = db.Column(db.DateTime, default=datetime.now)
    printed = db.Column(db.Boolean, default=False)
    order = db.relationship(
        "Order", backref=db.backref("goods_receipt", uselist=False),
        cascade="all, delete-orphan", uselist=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"))
    creator = db.relationship("User")

    def __init__(self, customer, unload_session, create_time=None, creator=None):
        self.customer = customer
        self.unload_session = unload_session
        self.create_time = create_time or datetime.now()
        self.creator = creator
        self.receipt_id = self.id_generator()

    def id_generator(self):
        return self.create_time.strftime('%Y%m%d%H%M%S') + \
               str((self.unload_session.id + self.customer.id) % 100)[0]

    def __unicode__(self):
        return self.receipt_id

    def __repr__(self):
        return "<GoodsReceipt %d>" % self.id


class GoodsReceiptEntry(db.Model):
    __modelname__ = u"收货单项"
    __tablename__ = "TB_GOODS_RECEIPT_ENTRY"

    id = db.Column(db.Integer, primary_key=True)
    goods_receipt_id = db.Column(db.Integer,
                                 db.ForeignKey("TB_GOODS_RECEIPT.id"))
    goods_receipt = db.relationship("GoodsReceipt",
                                    backref="goods_receipt_entries")
    weight = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("TB_PRODUCT.id"))
    product = db.relationship("Product")
    harbor_name = db.Column(db.String(32), db.ForeignKey('TB_HABOR.name'))
    harbor = db.relationship("Harbor")
    pic_path = db.Column(db.String(256))

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<GoodsReceiptProduct %d>" % self.id


class Order(db.Model):
    __modelname__ = u"订单"
    __tablename__ = "TB_ORDER"

    id = db.Column(db.Integer, primary_key=True)
    customer_order_number = db.Column(db.String(15), unique=True)
    goods_receipt_id = db.Column(db.Integer,
                                 db.ForeignKey('TB_GOODS_RECEIPT.id'))
    create_time = db.Column(db.DateTime)
    finish_time = db.Column(db.DateTime)
    sub_order_list = db.relationship(
        "SubOrder", backref="order",
        cascade="all, delete-orphan")
    dispatched = db.Column(db.Boolean)
    creator_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"))
    creator = db.relationship("User")
    refined = db.Column(db.Boolean, default=False)
    dispatched_time = db.Column(db.DateTime)

    def __init__(self, goods_receipt, creator,
                 create_time=None, finish_time=None, dispatched=False, refined=False):
        self.goods_receipt = goods_receipt
        self.create_time = create_time or datetime.now()
        self.finish_time = finish_time
        self.customer_order_number = goods_receipt.receipt_id
        self.dispatched = dispatched
        self.creator = creator
        self.refined = refined

    def __unicode__(self):
        return self.customer_order_number

    def __repr__(self):
        return "<Order %s>" % self.id


class SubOrder(db.Model, _ResyncMixin):
    __modelname__ = u"子订单"
    __tablename__ = "TB_SUB_ORDER"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("TB_PRODUCT.id"))
    product = db.relationship("Product")

    task_id = db.Column(db.Integer, db.ForeignKey("TB_UNLOAD_TASK.id"))
    unload_task = db.relationship("UnloadTask", backref=db.backref(
        "sub_order", uselist=False), uselist=False)

    default_harbor_name = db.Column(db.String(32), db.ForeignKey("TB_HABOR.name"))
    default_harbor = db.relationship("Harbor",
                                     primaryjoin="Harbor.name == SubOrder.default_harbor_name")
    spec = db.Column(db.String(64))
    type = db.Column(db.String(64))
    weight = db.Column(db.Integer, default=0)
    harbor_name = db.Column(db.String(32), db.ForeignKey('TB_HABOR.name'))
    harbor = db.relationship("Harbor",
                             primaryjoin="Harbor.name == SubOrder.harbor_name")
    order_id = db.Column(db.Integer, db.ForeignKey("TB_ORDER.id"))
    urgent = db.Column(db.Boolean)
    returned = db.Column(db.Boolean)
    pic_path = db.Column(db.String(256))
    tech_req = db.Column(db.String(64))
    create_time = db.Column(db.DateTime)
    finish_time = db.Column(db.DateTime)
    quantity = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(16), default=u'')
    due_time = db.Column(db.Date)
    order_type = db.Column(db.Integer)
    remaining_quantity = db.Column(db.Integer)
    work_command_list = db.relationship("WorkCommand",
                                        backref=db.backref(
                                            "sub_order", uselist=False),
                                        cascade="all, delete-orphan"
    )


    @property
    def unit_weight(self):
        try:
            return self.weight / float(self.quantity)
        except ZeroDivisionError:
            return 0

    def __init__(self, product, weight, harbor, order,
                 quantity, unit, order_type=constants.STANDARD_ORDER_TYPE,
                 create_time=None, finish_time=None, urgent=False,
                 returned=False, pic_path="", tech_req="", due_time=None,
                 spec="", type="", default_harbor=None):
        self.product = product
        self.spec = spec
        self.type = type
        self.weight = weight
        self.harbor = harbor
        self.remaining_quantity = self.quantity = quantity
        self.unit = unit
        self.order = order
        self.create_time = create_time or datetime.now()
        self.finish_time = finish_time
        self.urgent = urgent
        self.returned = returned
        self.pic_path = pic_path
        self.tech_req = tech_req
        self.due_time = due_time
        self.order_type = order_type
        self.default_harbor = default_harbor

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<SubOrder %d>" % self.id


class WorkCommand(db.Model, _ResyncMixin):
    __modelname__ = u"工单"
    __tablename__ = "TB_WORK_COMMAND"

    id = db.Column(db.Integer, primary_key=True)
    create_time = db.Column(db.DateTime)
    department = db.relationship("Department", order_by=User.id,
                                 backref="work_comman_list")
    department_id = db.Column(db.Integer, db.ForeignKey("TB_DEPARTMENT.id"),
                              nullable=True)
    last_mod = db.Column(db.DateTime, doc=u"上次对工单修改的时间")
    completed_time = db.Column(db.DateTime, doc=u"生产完毕的时间")
    org_cnt = db.Column(db.Integer)
    org_weight = db.Column(db.Integer)
    urgent = db.Column(db.Boolean)
    previous_procedure_id = db.Column(db.Integer,
                                      db.ForeignKey("TB_PROCEDURE.id"))
    previous_procedure = db.relationship("Procedure",
                                         primaryjoin="Procedure"
                                                     ".id==WorkCommand"
                                                     ".previous_procedure_id")
    procedure_id = db.Column(db.Integer, db.ForeignKey("TB_PROCEDURE.id"))
    procedure = db.relationship("Procedure",
                                primaryjoin="Procedure.id==WorkCommand"
                                            ".procedure_id")
    processed_cnt = db.Column(db.Integer)
    processed_weight = db.Column(db.Integer)
    status = db.Column(db.Integer)
    sub_order_id = db.Column(db.Integer, db.ForeignKey("TB_SUB_ORDER.id"))
    tag = db.Column(db.String(32))
    team = db.relationship("Team", backref="work_comman_list")
    team_id = db.Column(db.Integer, db.ForeignKey("TB_TEAM.id"), nullable=True)
    tech_req = db.Column(db.String(32))
    qir_list = db.relationship("QIReport", backref="work_command",
                               cascade="all, delete-orphan",
                               primaryjoin="WorkCommand.id==QIReport"
                                           ".work_command_id")
    pic_path = db.Column(db.String(256))
    handle_type = db.Column(db.Integer)
    previous_work_command_id = db.Column(db.Integer, db.ForeignKey("TB_WORK_COMMAND.id"))
    previous_work_command = db.relationship("WorkCommand", backref=db.backref("next_work_command_list"),
                                            primaryjoin="WorkCommand.id==WorkCommand.previous_work_command_id",
                                            uselist=False, remote_side=id)

    @property
    def unit_weight(self):
        try:
            return self.org_weight / float(self.org_cnt)
        except ZeroDivisionError:
            return 0

    @property
    def processed_unit_weight(self):
        try:
            return self.processed_weight / float(self.processed_cnt)
        except ZeroDivisionError:
            return 0

    def __init__(self, sub_order, org_weight, procedure, urgent=False,
                 status=constants.work_command.STATUS_DISPATCHING, department=None,
                 create_time=None,
                 last_mod=datetime.now(),
                 processed_weight=0, team=None, previous_procedure=None,
                 tag="", tech_req="", org_cnt=0, processed_cnt=0, pic_path="",
                 handle_type=constants.work_command.HT_NORMAL,
                 previous_work_command=None):
        self.sub_order = sub_order
        self.urgent = urgent
        self.org_weight = org_weight
        self.procedure = procedure
        self.status = status
        self.create_time = create_time or datetime.now()
        self.last_mod = last_mod
        self.processed_weight = processed_weight
        self.team = team
        self.department = department
        self.previous_procedure = previous_procedure
        self.tag = tag
        self.tech_req = tech_req
        self.org_cnt = org_cnt
        self.processed_cnt = processed_cnt
        self.pic_path = pic_path
        self.handle_type = handle_type
        self.previous_work_command = previous_work_command

    def set_status(self, new_status):
        """
        set new status, and UPDATE last_mod field, so DON'T UPDATE STATUS
        DIRECTLY!
        """
        self.status = new_status
        self.last_mod = datetime.now()

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<WorkCommand %d>" % self.id


class QIReport(db.Model):
    __modelname__ = u"质检报告"
    __tablename__ = "TB_QI_REPORT"

    id = db.Column(db.Integer, primary_key=True)
    work_command_id = db.Column(db.Integer,
                                db.ForeignKey("TB_WORK_COMMAND.id"))
    generated_work_command_id = db.Column(db.Integer,
                                          db.ForeignKey("TB_WORK_COMMAND.id"))
    generated_work_command = db.relationship("WorkCommand",
                                             backref=db.backref("parent_qir",
                                                                uselist=False),
                                             primaryjoin="WorkCommand.id==QIReport.generated_work_command_id")
    quantity = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    result = db.Column(db.Integer)
    report_time = db.Column(db.DateTime)
    actor_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"))
    actor = db.relationship(User)
    pic_path = db.Column(db.String(256))

    def __init__(self, work_command, quantity, weight, result, actor_id,
                 report_time=None, pic_path=""):
        self.work_command = work_command
        self.quantity = quantity
        self.weight = weight
        self.result = result
        self.actor_id = actor_id
        self.report_time = report_time or datetime.now()
        self.pic_path = pic_path

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<QIReport %d>" % self.id

class DeliverySession(db.Model):
    __modelname__ = u"发货会话"
    __tablename__ = "TB_DELIVERY_SESSION"

    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(32), db.ForeignKey("TB_PLATE.name"), nullable=False)
    plate_ = db.relationship("Plate")
    tare = db.Column(db.Integer, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now)
    finish_time = db.Column(db.DateTime)
    with_person = db.Column(db.Boolean, default=False)
    delivery_task_list = db.relationship("DeliveryTask",
                                         backref=db.backref("delivery_session",
                                                            uselist=False),
                                         cascade="all, delete-orphan")
    status = db.Column(db.Integer, default=constants.delivery.STATUS_LOADING, nullable=False)

    def __unicode__(self):
        return self.plate

    def __repr__(self):
        return "<DeliverySession %d>" % self.id


class StoreBill(db.Model):
    __modelname__ = u"仓单"
    __tablename__ = "TB_STORE_BILL"

    id = db.Column(db.Integer, primary_key=True)

    harbor_name = db.Column(db.String(32), db.ForeignKey('TB_HABOR.name'))
    harbor = db.relationship("Harbor")
    sub_order_id = db.Column(db.Integer, db.ForeignKey("TB_SUB_ORDER.id"))
    sub_order = db.relationship("SubOrder",
                                backref=db.backref("store_bill_list",
                                                   cascade="all, delete-orphan"))
    qir_id = db.Column(db.Integer, db.ForeignKey("TB_QI_REPORT.id"))
    qir = db.relationship("QIReport",
                          backref=db.backref("store_bill_list",
                                             cascade="all"))
    quantity = db.Column(db.Integer)
    weight = db.Column(db.Integer, default=0)
    customer_id = db.Column(db.Integer, db.ForeignKey("TB_CUSTOMER.id"))
    customer = db.relationship("Customer")
    delivery_session_id = db.Column(db.Integer,
                                    db.ForeignKey("TB_DELIVERY_SESSION.id"),
                                    nullable=True)
    delivery_session = db.relationship("DeliverySession",
                                       backref="store_bill_list")
    delivery_task_id = db.Column(db.Integer,
                                 db.ForeignKey("TB_DELIVERY_TASK.id"),
                                 nullable=True)
    delivery_task = db.relationship("DeliveryTask", backref="store_bill_list")
    create_time = db.Column(db.DateTime)
    printed = db.Column(db.Boolean, default=False)

    @property
    def unit_weight(self):
        try:
            return self.weight / float(self.quantity)
        except ZeroDivisionError:
            return 0

    def __init__(self, qir, create_time=None):
        self.qir = qir
        self.weight = qir.weight
        self.quantity = qir.quantity
        self.customer_id = qir.work_command.sub_order.order.goods_receipt \
            .customer_id
        self.create_time = create_time or datetime.now()
        self.sub_order = qir.work_command.sub_order


    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<StoreBill %d>" % self.id

class DeliveryTask(db.Model):
    __modelname__ = u"发货任务"
    __tablename__ = "TB_DELIVERY_TASK"

    id = db.Column(db.Integer, primary_key=True)
    delivery_session_id = db.Column(db.Integer,
                                    db.ForeignKey("TB_DELIVERY_SESSION.id"))
    actor_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"))
    actor = db.relationship("User")
    create_time = db.Column(db.DateTime, default=datetime.now)
    quantity = db.Column(db.Integer)
    weight = db.Column(db.Integer, default=0)
    returned_weight = db.Column(db.Integer, default=0)
    is_last = db.Column(db.Boolean, default=False)

    def __init__(self, delivery_session, actor_id,
                 create_time=None):
        self.delivery_session = delivery_session
        self.actor_id = actor_id
        self.create_time = create_time or datetime.now()

    @property
    def customer(self):
        if self.store_bill_list:
            return self.store_bill_list[0].customer
        else:
            return ""

    @property
    def product(self):
        if self.store_bill_list:
            sb = self.store_bill_list[0]
            return sb.qir.work_command.sub_order.product
        else:
            return ""

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<DeliveryTask %d>" % self.id


class Consignment(db.Model):
    __modelname__ = u"发货单"
    __tablename__ = "TB_CONSIGNMENT"

    id = db.Column(db.Integer, primary_key=True)
    consignment_id = db.Column(db.String(15), unique=True)
    delivery_session_id = db.Column(db.Integer,
                                    db.ForeignKey("TB_DELIVERY_SESSION.id"))
    delivery_session = db.relationship("DeliverySession",
                                       backref="consignment_list")
    actor_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"))
    actor = db.relationship("User")
    create_time = db.Column(db.DateTime, default=datetime.now)
    customer_id = db.Column(db.Integer, db.ForeignKey("TB_CUSTOMER.id"))
    customer = db.relationship("Customer")
    pay_in_cash = db.Column(db.Boolean, default=False)
    is_paid = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(256))
    MSSQL_ID = db.Column(db.Integer)
    stale = db.Column(db.Boolean, default=False)

    def __init__(self, customer, delivery_session, pay_in_cash,
                 create_time=None):
        self.delivery_session = delivery_session
        self.customer = customer
        self.pay_in_cash = pay_in_cash
        self.create_time = create_time or datetime.now()
        self.consignment_id = self.id_generator()

    def id_generator(self):
        return self.create_time.strftime('%Y%m%d%H%M%S') + \
               str((self.delivery_session.id + self.customer.id) % 100)[0]

    def __unicode__(self):
        return unicode(self.consignment_id)

    def __repr__(self):
        return "<Consignment %d>" % self.id


class Procedure(db.Model):
    __modelname__ = u"工序"
    __tablename__ = "TB_PROCEDURE"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True)
    department_list = db.relationship("Department",
                                      secondary=procedure_and_department_table,
                                      backref="procedure_list", doc=u"只有这里罗列的车间允许执行此工序")

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<Procedure %d>" % self.id


class Deduction(db.Model):
    __modelname__ = u"扣重记录"
    __tablename__ = "TB_DEDUCTION"

    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Integer, doc=u"单位为公斤", nullable=False)
    work_command_id = db.Column(db.Integer,
                                db.ForeignKey("TB_WORK_COMMAND.id"))
    work_command = db.relationship("WorkCommand", backref="deduction_list")
    team_id = db.Column(db.Integer, db.ForeignKey("TB_TEAM.id"),
                        nullable=False)
    team = db.relationship("Team", backref="deduction_list")
    actor_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"),
                         nullable=False)
    actor = db.relationship(User)
    create_time = db.Column(db.DateTime, default=datetime.now)
    remark = db.Column(db.String(256))

    def __init__(self, weight=None, actor=None, team=None, work_command=None,
                 create_time=None, remark=None):
        self.weight = weight
        self.work_command = work_command
        self.actor = actor
        self.team = team
        self.create_time = create_time or datetime.now()
        self.remark = remark

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<Deduction %d>" % self.id


class ConsignmentProduct(db.Model):
    __modelname__ = u"发货单产品"
    __tablename__ = "TB_CONSIGNMENT_PRODUCT"

    id = db.Column(db.Integer, primary_key=True)
    consignment_id = db.Column(db.Integer, db.ForeignKey("TB_CONSIGNMENT.id"),
                               nullable=False)
    consignment = db.relationship("Consignment", backref=db.backref("product_list", cascade="all, delete-orphan"))
    product_id = db.Column(db.Integer, db.ForeignKey("TB_PRODUCT.id"),
                           nullable=False)
    product = db.relationship("Product")
    delivery_task_id = db.Column(db.Integer,
                                 db.ForeignKey("TB_DELIVERY_TASK.id"),
                                 nullable=False)
    delivery_task = db.relationship("DeliveryTask")
    weight = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    unit = db.Column(db.String(16), default=u"桶")
    spec = db.Column(db.String(64))
    type = db.Column(db.String(64))
    returned_weight = db.Column(db.Integer)
    team_id = db.Column(db.Integer, db.ForeignKey("TB_TEAM.id"))
    team = db.relationship("Team")

    def __init__(self, product, delivery_task, consignment):
        self.product = product
        self.delivery_task = delivery_task
        self.consignment = consignment

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return "<DeliveryProduct %d>" % self.id


class Plate(db.Model):
    __modelname__ = u"车辆"
    __col_desc__ = {
        u"车牌号": "name"
    }
    __tablename__ = "TB_PLATE"

    name = db.Column(db.String(64), primary_key=True)

    def __init__(self, name):
        self.name = name

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<Plate %s>" % self.name

class Log(db.Model):
    __modelname__ = u"操作记录"
    __tablename__ = "TB_LOG"

    # MAIN PART
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"))
    actor = db.relationship("User")
    obj_cls = db.Column(db.String(64))
    obj_pk = db.Column(db.String(64))
    obj = db.Column(db.String(64))
    action = db.Column(db.String(64))
    create_time = db.Column(db.DateTime, default=datetime.now)


    # SUPPLEMENT PART
    name = db.Column(db.String(64))
    level = db.Column(db.String(64))
    module = db.Column(db.String(64))
    func_name = db.Column(db.String(64))
    line_no = db.Column(db.Integer)
    thread = db.Column(db.Integer)
    thread_name = db.Column(db.String(64))
    process = db.Column(db.Integer)
    message = db.Column(db.String(256))
    args = db.Column(db.String(64))
    extra = db.Column(db.String(64))


    def __unicode__(self):
        return u"[%s]: 用户%s对%s(%s)执行了(%s)操作" % (
        self.create_time.strftime("%Y-%m-%d %H:%M:%S"), self.actor.username,
        self.obj_cls, self.obj, self.action)

class TODO(db.Model):
    __modelname__ = u"待办事项"
    __tablename__ = "TB_TODO"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"))
    user = db.relationship("User", primaryjoin="TODO.user_id==User.id")
    obj_pk = db.Column(db.String(64))
    create_time = db.Column(db.DateTime, default=datetime.now)
    actor_id = db.Column(db.Integer, db.ForeignKey("TB_USER.id"))
    actor = db.relationship("User", primaryjoin="TODO.actor_id==User.id")
    action = db.Column(db.String(64))
    priority = db.Column(db.Integer)
    msg = db.Column(db.String(128))
    context_url = db.Column(db.String(256))


class Config(db.Model):
    __modelname__ = u"配置项"
    __tablename__ = "TB_CONFIG"

    id = db.Column(db.Integer, primary_key=True)
    property_name = db.Column(db.String(64), nullable=False)
    property_desc = db.Column(db.String(64))
    property_value = db.Column(db.String(64), nullable=False)

    def __unicode__(self):
        return self.property_name


from yawf.node_mixin import NodeMixin


class Node(db.Model, NodeMixin):
    __tablename__ = 'TB_NODE'
    __modelname__ = '工作流节点'

    @declared_attr
    def handler_group_id(self):
        return db.Column(db.Integer, db.ForeignKey('TB_GROUP.id'))

    @declared_attr
    def handler_group(self):
        return db.relationship('Group')

