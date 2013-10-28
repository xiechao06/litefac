#-*- coding:utf-8 -*-
from flask import request, redirect, url_for
from flask.ext.login import login_required
from werkzeug.utils import cached_property
from flask.ext.databrowser import ModelView, filters
from flask.ext.databrowser.column_spec import ColumnSpec, InputColumnSpec, ImageColumnSpec, PlaceHolderColumnSpec
from flask.ext.principal import PermissionDenied
from wtforms.validators import Required
from litefac import models
from litefac.apis.delivery import StoreBillWrapper
from litefac.permissions import QualityInspectorPermission
from litefac.portal.store import store_bill_page
from litefac.utilities import decorators, _

_printed = u"<i class='icon-ticket' title='已打印'></i>"
_unprinted = u"<i class='icon-check-empty' title='未打印'></i>"


class StoreBillModelView(ModelView):

    __default_order__ = ("id", "desc")

    __list_columns__ = ["id", "customer", "product", "weight", "quantity", "sub_order.order.customer_order_number",
                        "qir.actor", "printed", "create_time", "qir.work_command.id", "harbor"]

    __column_labels__ = {"id": u"仓单号",
                         "customer": u"客户",
                         "product": u"产品",
                         "weight": u"重量",
                         "quantity": u"数量",
                         "sub_order.order.customer_order_number": u"订单号",
                         "qir.actor": u"质检员",
                         "create_time": u"创建时间",
                         "qir.work_command.id": u"工单号",
                         "printed": u"打印",
                         "harbor": u"存放点",
                         "pic_url": u"图片"}

    __column_formatters__ = {"printed": lambda v, obj: _printed if v else _unprinted,
                             "harbor": lambda v, model: v if v else ""}

    def preprocess(self, obj):
        return StoreBillWrapper(obj)

    def try_create(self):
        raise PermissionDenied

    class Undeliveried(filters.Only):
        def set_sa_criterion(self, q):
            if self.value:
                return q.filter(models.StoreBill.delivery_session == None).filter(models.StoreBill.delivery_task == None)
            else:
                return q

        @cached_property
        def attr(self):
            return self.col_name

    __column_filters__ = [filters.EqualTo("customer", u"是"),
                          filters.Only("printed", display_col_name=u"只展示未打印", test=lambda v: v == False,
                                       notation="__only_printed"),
                          Undeliveried("undeliveried", display_col_name=u"只展示未发货", test=None,
                                       notation="__undeliveried")
                          ]

    def try_edit(self, processed_objs=None):
        def _try_edit(obj):
            if obj and obj.delivery_session and obj.delivery_task:
                raise PermissionDenied
        QualityInspectorPermission.test()
        if isinstance(processed_objs, (list, tuple)):
            for obj in processed_objs:
                _try_edit(obj)
        else:
            _try_edit(processed_objs)

    def edit_hint_message(self, obj, read_only=False):
        if read_only:
            if QualityInspectorPermission.can():
                return u"仓单-%s已发货，不能编辑" % obj.id
            else:
                return u"您没有修改的权限"
        else:
            return super(StoreBillModelView, self).edit_hint_message(obj, read_only)

    __form_columns__ = [ColumnSpec("id"), "qir.work_command.id", "customer", "product",
                        InputColumnSpec("harbor", validators=[Required(u"不能为空")]), "weight", "quantity",
                        ColumnSpec("unit", label=u"单位"), ColumnSpec("sub_order.spec", label=u"型号"),
                        ColumnSpec("sub_order.type", label=u"规格"), ColumnSpec("create_time"),
                        ColumnSpec("printed", label=u"是否打印", formatter=lambda v, obj: u"是" if v else u"否"),
                        ColumnSpec("sub_order.id", label=u"子订单号"), "sub_order.order.customer_order_number",
                        ImageColumnSpec("pic_url", label=u"图片"),
                        PlaceHolderColumnSpec("log_list", label=u"日志", template_fname="logs-snippet.html")]

    def get_customized_actions(self, processed_objs=None):
        if QualityInspectorPermission.can():
            from .actions import PreviewPrintAction
            return [PreviewPrintAction(u"打印预览")]
        else:
            return []

    @login_required
    def try_view(self, processed_objs=None):
        pass
store_bill_view = StoreBillModelView(models.StoreBill, u"仓单")



@store_bill_page.route('/')
def index():
    return redirect(url_for("store_bill.store_bill_list"))

@store_bill_page.route("/store-bill-preview/<int:id_>", methods=["GET", "POST"])
@decorators.templated("/store/store-bill-preview.html")
@decorators.nav_bar_set
def store_bill_preview(id_):
    import litefac.apis as apis

    store_bill = apis.delivery.get_store_bill(id_)
    if store_bill:
        if request.method == "GET":
            return dict(titlename=u'仓单详情', store_bill=store_bill)
    else:
        return _("没有此仓单%(id)d" % {"id": id_}), 404
