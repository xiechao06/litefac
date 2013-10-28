# -*- coding: UTF-8 -*-
import os
from sqlalchemy.exc import SQLAlchemyError
from flask import (Flask, render_template, request, session, g, url_for, _request_ctx_stack,
                   current_app)
from flask.ext.babel import Babel, gettext
from flask.ext.nav_bar import FlaskNavBar
from flask.ext.login import login_user

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("litefac.default_settings")
if "LITE_FAC_HOME" in os.environ:
    app.config.from_pyfile(
        os.path.join(os.environ["LITE_FAC_HOME"], "config.py"), silent=True)
app.config.from_pyfile(os.path.join(os.getcwd(), "config.py"), silent=True)
from flask.ext.login import LoginManager, current_user
login_manager = LoginManager()
login_manager.init_app(app)
from flask.ext.principal import Principal, Permission

import yawf

from litefac.database import db
from litefac import models
yawf.WorkFlowEngine(db, models.Node)
import yawf.models
from litefac.apis.delivery import CreateDeliveryTaskWithAbnormalWeight, PermitDeliveryTaskWithAbnormalWeight
yawf.register_policy(CreateDeliveryTaskWithAbnormalWeight)
yawf.register_policy(PermitDeliveryTaskWithAbnormalWeight)

principal = Principal(app)

import logging
import logging.handlers

logging.basicConfig(level=logging.DEBUG)

file_handler = logging.handlers.TimedRotatingFileHandler(
    app.config["LOG_FILE"], 'D', 1, 10, "utf-8")
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
file_handler.suffix = "%Y%m%d.log"
app.logger.addHandler(file_handler)

from litefac.log.handler import DBHandler
timeline_logger = logging.getLogger("timeline")
timeline_logger.addHandler(DBHandler())
# create upload files

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

babel = Babel(app)

nav_bar = FlaskNavBar(app)

from flask.ext.databrowser import DataBrowser
from litefac.database import db
from litefac import constants
data_browser = DataBrowser(app, db, page_size=constants.ITEMS_PER_PAGE, logger=timeline_logger)

# ============== REGISTER BLUEPRINT ========================
serve_web = app.config["SERVE_TYPE"] in ["both", "web"]
serve_ws = app.config["SERVE_TYPE"] in ["both", "ws"]


if serve_web:

    from litefac.portal.report import report_page
    from flask.ext.report import FlaskReport
    from flask.ext.report.utils import collect_models
    from litefac import models

    def collect_model_names():
        ret = {}

        for k, v in models.__dict__.items():
            if hasattr(v, '_sa_class_manager'):
                ret[v.__tablename__] = v.__modelname__
        return ret

    class _FlaskReport(FlaskReport):

        def try_view_report(self):
            Permission.union(AdminPermission, AccountantPermission).test()

        def try_edit_data_set(self):
            Permission.union(AdminPermission, AccountantPermission).test()

        def try_edit_notification(self):
            AdminPermission.test()

    _FlaskReport(db, collect_models(models), app, report_page, {
        'report_list': {
            'nav_bar': nav_bar,
        },
        'report': {
            'nav_bar': nav_bar,
        },
        'data_set': {
            'nav_bar': nav_bar,
        },
        'data_sets': {
            'nav_bar': nav_bar,
        },
        'notification_list': {
            'nav_bar': nav_bar,
        },
        'notification': {
            'nav_bar': nav_bar,
        }
    },
    collect_model_names())
    app.register_blueprint(report_page, url_prefix="/report")
    from litefac.portal.store import store_bill_page
    app.register_blueprint(store_bill_page, url_prefix="/store")
    from litefac.portal.deduction import deduction_page
    app.register_blueprint(deduction_page, url_prefix="/deduction")
    from litefac.portal.auth import auth
    app.register_blueprint(auth, url_prefix="/auth")
    from litefac.portal.cargo import cargo_page, gr_page
    app.register_blueprint(cargo_page, url_prefix='/cargo')
    app.register_blueprint(gr_page, url_prefix='/goods_receipt')
    from litefac.portal.delivery import delivery_page, consignment_page
    app.register_blueprint(delivery_page, url_prefix='/delivery')
    app.register_blueprint(consignment_page, url_prefix='/consignment')
    from litefac.portal.misc import misc
    app.register_blueprint(misc, url_prefix="/misc")
    from litefac.portal.manufacture import manufacture_page
    app.register_blueprint(manufacture_page, url_prefix="/manufacture")
    from litefac.portal.order import order_page
    app.register_blueprint(order_page, url_prefix="/order")
    from litefac.portal.op import op_page
    app.register_blueprint(op_page, url_prefix="/op")
    from litefac.portal.admin2 import admin2_page
    app.register_blueprint(admin2_page, url_prefix="/admin2")

    from litefac.portal.import_data import import_data_page
    app.register_blueprint(import_data_page, url_prefix="/import_data")
    from litefac.portal.search import search_page
    app.register_blueprint(search_page, url_prefix="/search")

    from litefac.portal.timeline import time_line_page
    app.register_blueprint(time_line_page, url_prefix="/timeline")

    from litefac.portal.todo import to_do_page
    app.register_blueprint(to_do_page, url_prefix="/todo")

    from litefac.portal.quality_inspection import qir_page
    app.register_blueprint(qir_page, url_prefix="/qir")

    from litefac.portal.dashboard import dashboard
    app.register_blueprint(dashboard, url_prefix="/dashboard")

    from litefac.portal.work_flow import work_flow_page
    app.register_blueprint(work_flow_page, url_prefix="/work-flow")

if serve_ws:

    from litefac.portal.auth_ws import auth_ws
    app.register_blueprint(auth_ws, url_prefix="/auth_ws")
    from litefac.portal.cargo_ws import cargo_ws
    app.register_blueprint(cargo_ws, url_prefix='/cargo_ws')
    from litefac.portal.delivery_ws import delivery_ws
    app.register_blueprint(delivery_ws, url_prefix='/delivery_ws')
    from litefac.portal.order_ws import order_ws
    app.register_blueprint(order_ws, url_prefix="/order_ws")
    from litefac.portal.manufacture_ws import manufacture_ws
    app.register_blueprint(manufacture_ws, url_prefix="/manufacture_ws")


# ====================== REGISTER NAV BAR ===================================
from litefac.permissions.roles import (CargoClerkPermission, AccountantPermission, QualityInspectorPermission,
                                        DepartmentLeaderPermission, AdminPermission, SchedulerPermission)
from litefac.permissions.order import view_order, schedule_order
from litefac.permissions.work_command import view_work_command
nav_bar.register(cargo_page, name=u"卸货会话", permissions=[CargoClerkPermission], group=u"卸货管理")
nav_bar.register(gr_page, name=u"收货单", permissions=[CargoClerkPermission], group=u"卸货管理")
nav_bar.register(order_page, default_url='/order/order-list', name=u"订单管理",
                 permissions=[view_order])
nav_bar.register(order_page, default_url='/order/order-list', name=u"订单管理",
                 permissions=[schedule_order])
nav_bar.register(delivery_page, name=u'发货会话',
                 permissions=[CargoClerkPermission], group=u"发货管理")
nav_bar.register(consignment_page, name=u'发货单',
                 permissions=[CargoClerkPermission.union(AccountantPermission)], group=u"发货管理")
nav_bar.register(manufacture_page, name=u"工单管理",
                 permissions=[SchedulerPermission])
#nav_bar.register(delivery_page, name=u"发货单管理",
                 #default_url="/delivery/consignment-list",
                 #permissions=[AccountantPermission])
nav_bar.register(manufacture_page, name=u"质检管理",
                 default_url="/manufacture/qir-list",
                 permissions=[DepartmentLeaderPermission])
nav_bar.register(store_bill_page, name=u"仓单管理",
                 default_url="/store/store-bill-list",
                 permissions=[QualityInspectorPermission])
nav_bar.register(deduction_page, name=u"扣重管理", default_url="/deduction/",
                 permissions=[QualityInspectorPermission])
nav_bar.register(dashboard, name=u"仪表盘", permissions=[AdminPermission])

nav_bar.register(time_line_page, name=u"时间线", default_url="/timeline/log-list")
nav_bar.register(search_page, name=u"搜索", default_url="/search/search")
nav_bar.register(admin2_page, name=u"管理中心", default_url="/admin2/user-list", permissions=[AdminPermission])
nav_bar.register(report_page, name=u"报表列表", default_url="/report/report-list", permissions=[Permission.union(AdminPermission, AccountantPermission)], group=u'报表',
                 enabler=lambda nav: request.path.startswith('/report/report'))
nav_bar.register(report_page, name=u"数据集合列表", default_url="/report/data-sets", permissions=[Permission.union(AdminPermission, AccountantPermission)], group=u'报表',
                 enabler=lambda nav: request.path.startswith('/report/data-set'))
nav_bar.register(report_page, name=u"推送列表", default_url="/report/notification-list", permissions=[Permission.union(AdminPermission, AccountantPermission)], group=u'报表',
                 enabler=lambda nav: request.path.startswith('/report/notification-list'))
nav_bar.register(to_do_page, name=u"待办事项", default_url="/todo/todo-list")
nav_bar.register(work_flow_page, name=lambda: u"工作流(%d)" % models.Node.query.filter(models.Node.handle_time==None).count(),
                 default_url="/work-flow/node-list", permissions=[CargoClerkPermission])

#install jinja utilities
from litefac.utilities import url_for_other_page, datetimeformat
from litefac.utilities.decorators import after_this_request
from litefac import permissions

app.jinja_env.globals['url_for_other_page'] = url_for_other_page
app.jinja_env.globals['permissions'] = permissions
app.jinja_env.filters['_datetimeformat'] = datetimeformat
app.jinja_env.add_extension("jinja2.ext.loopcontrols")

from flask.ext.principal import (identity_loaded, RoleNeed, UserNeed,
                                 PermissionDenied, identity_changed, Identity)

@login_manager.user_loader
def load_user(user_id):
    from litefac.apis import auth
    return auth.get_user(user_id)


from litefac.permissions.work_flow import HandleNodeNeed

@identity_loaded.connect_via(app)
def permission_handler(sender, identity):

    from flask.ext import login

    identity.user = login.current_user
    if not identity.user:
        return
    if hasattr(identity.user, 'id'):
        identity.provides.add(UserNeed(unicode(identity.user.id)))

    if hasattr(identity.user, 'groups'):
        current_group_id = session.get('current_group_id')
        if current_group_id is None:
            current_group_id = request.cookies.get('current_group_id')
        if current_group_id is None:
            group = identity.user.groups[0]
        else:
            for group_ in identity.user.groups:
                if group_.id == current_group_id:
                    group = group_
                    break
            else:
                group = identity.user.default_group or identity.user.groups[0]
        session['current_group_id'] = group.id
        identity.provides.add(RoleNeed(unicode(group.id)))

    if hasattr(identity.user, 'permissions'):
        for perm in identity.user.permissions:
            try:
                for need in permissions.permissions[perm.name]["needs"]:
                    identity.provides.add(need)
            except KeyError:
                pass

    if os.path.dirname(request.path) == os.path.dirname(url_for('work_flow.node', id_=-1)):
        node = models.Node.query.get(os.path.basename(request.path))
        if node:
            if node.handler_group_id == current_user.group.id:
                identity.provides.add(HandleNodeNeed)

#设置无权限处理器
@app.errorhandler(PermissionDenied)
@app.errorhandler(401)
def permission_denied(error):

    #如果用户已登录则显示无权限页面
    from flask import redirect, url_for
    if not current_user.is_anonymous():
        return redirect(url_for("error", msg=u'请联系管理员获得访问权限!',
                                back_url=request.args.get("url")))
    return render_template("auth/login.html",
                           error=gettext(u"请登录"), next_url=request.url, titlename=u"请登录")

if not app.debug:
    def sender_email(traceback):
        from flask.ext.mail import Mail, Message

        mail = Mail(app)
        senders = app.config.get("SENDERS", [])
        if not senders:
            return
        msg = Message(subject=u"%s %s时遇到异常" % (request.method, request.url),
                      html=traceback.render_summary(),
                      sender="litefac@163.com",
                      recipients=senders)
        mail.send(msg)

    @app.errorhandler(Exception)
    def error(error):
        if isinstance(error, SQLAlchemyError):
            from litefac.database import db

            db.session.rollback()
        from werkzeug.debug.tbtools import get_current_traceback

        traceback = get_current_traceback(skip=1, show_hidden_frames=False,
                                          ignore_system_exceptions=True)
        app.logger.error("%s %s" % (request.method, request.url))
        app.logger.error(traceback.plaintext)
        sender_email(traceback)
        return render_template("error.html", msg=u"%s %s时，系统异常" % (request.method, request.url),
                               detail=traceback.render_summary(),
                               back_url=request.args.get("back_url", "/"),
                               nav_bar=nav_bar, titlename=u"错误"), 403


@app.after_request
def call_after_request_callbacks(response):
    for callback in getattr(g, 'after_request_callbacks', ()):
        response = callback(response)
    return response


@app.before_request
def _():
    from litefac import apis

    # 需要以guest用户身份登录
    if _request_ctx_stack.top:
        user = apis.auth.authenticate('guest', 'guest')
        login_user(user)
        identity_changed.send(current_app._get_current_object(),
                            identity=Identity(user.id))
    #g.locale = get_locale()

from work_flow_repr import Event
from work_flow_repr.utils import ModelNode, annotate_model
from litefac.models import (GoodsReceipt, Order, SubOrder, WorkCommand, Log, StoreBill)

class GoodsReceiptNode(ModelNode):
    @property
    def name(self):
        return u"收货单" + unicode(self.obj)

    @property
    def description(self):
        return render_template("work_flow_repr/goods_receipt.html", goods_receipt=self.obj)

    @property
    def events(self):
        return [
            Event(self.obj.unload_session.create_time, u'开始卸货', _get_username(self.obj.creator) if self.obj.creator else ''),
            Event(self.obj.unload_session.finish_time, u'卸货完毕', ",".join(
                _get_username(task.creator) for task in self.obj.unload_session.task_list)),
            Event(self.obj.order.create_time, u'生成订单', self.obj.order.creator.username),
        ]

    @property
    def target(self):
        return data_browser.get_form_url(self.obj)

    @property
    def children_model_groups(self):
        return [(u'订单', [self.obj.order]),]

class OrderNode(ModelNode):

    @property
    def name(self):
        return u"订单" + unicode(self.obj)

    @property
    def description(self):
        return ''

    @property
    def target(self):
        return data_browser.get_form_url(self.obj)

    @property
    def events(self):
        ret = [
            Event(self.obj.create_time, u'创建', _get_username(self.obj.creator), description=u'[%s] 创建' % str(self.obj.create_time), by=u'生成订单'),
        ]
        if self.obj.dispatched:
            ret.append(Event(self.obj.dispatched_time, u'下发订单',  _get_username(self.obj.creator), description=u'[%s] 下发' % str(self.obj.dispatched_time)))
        return ret

    @property
    def children_model_groups(self):
        return [(u'子订单', self.obj.sub_order_list)]

class SubOrderNode(ModelNode):

    @property
    def name(self):
        return u"子订单" + unicode(self.obj)

    @property
    def description(self):
        return render_template("work_flow_repr/sub_order.html", sub_order=self.obj)

    @property
    def target(self):
        return data_browser.get_form_url(self.obj)

    @property
    def events(self):
        ret = [
            Event(self.obj.create_time, u'创建', _get_username(self.obj.order.creator), by=u'生成子订单'),
        ]

        for wc in self.obj.work_command_list:
            if wc.cause == constants.work_command.CAUSE_NORMAL:
                ret.append(Event(wc.create_time, u'预排产', _get_username(self.obj.order.creator)))
        return ret

    @property
    def children_model_groups(self):
        return [(u'预排产工单', [wc for wc in self.obj.work_command_list if wc.cause == constants.work_command.CAUSE_NORMAL]),]

class WorkCommandNode(ModelNode):

    @property
    def name(self):
        return u"工单" + unicode(self.obj)

    @property
    def description(self):
        return render_template('work_flow_repr/work-command.html', work_command=self.obj)

    @property
    def target(self):
        return data_browser.get_form_url(self.obj)

    @property
    def events(self):
        logs = Log.query.filter(Log.obj_cls == self.obj.model.__class__.__name__).filter(
            Log.obj_pk == self.obj.id).filter(Log.action != u'<增加重量>').filter(Log.action != u'新建').all()
        return [Event(self.obj.create_time, u'新建', _get_username(self.obj.order.creator),
                      u'[%s]: 创建' % self.obj.create_time)] + [
                   Event(log.create_time, log.action.strip('<>'), _get_username(self.obj.order.creator),
                         u'[%s] %s' % (str(log.create_time), log.action.strip('<>'))) for log in logs]

    @property
    def children_model_groups(self):
        d = {}
        for wc in self.obj.next_work_command_list:
            d.setdefault(wc.cause, []).append(wc)

        store_bills = []
        for qir in self.obj.qir_list:
            for sb in qir.store_bill_list[:1]:
                store_bills.append(sb)

        return [(k, v) for k, v in d.items()] + [('仓单', store_bills)]

class StoreBillNode(ModelNode):

    @property
    def name(self):
        return u"仓单" + unicode(self.obj)

    @property
    def description(self):
        return render_template('work_flow_repr/store-bill.html', store_bill=self.obj)

    @property
    def target(self):
        return data_browser.get_form_url(self.obj)

    @property
    def events(self):
        ret = [
            Event(self.obj.create_time, u'创建', _get_username(self.obj.qir.actor), by='创建仓单', description=u'[%s] 创建' % str(self.obj.create_time))
        ]
        if self.obj.delivery_task:
            ret.append(Event(self.obj.delivery_task.create_time, u'发货', _get_username(self.obj.delivery_task.actor), description=u'[%s] 发货' % str(self.obj.delivery_task.create_time)))
        return ret

    @property
    def children_model_groups(self):
        next_store_bill_list = self.obj.next_store_bill_list
        if next_store_bill_list:
            return [(u'仓单', next_store_bill_list)]
        return []


def _get_username(obj):
    return obj.username if obj is not None else ""

annotate_model(GoodsReceipt, GoodsReceiptNode)
annotate_model(Order, OrderNode)
annotate_model(SubOrder, SubOrderNode)
annotate_model(WorkCommand, WorkCommandNode)
annotate_model(StoreBill, StoreBillNode)

