# -*- coding: utf-8 -*-
from collections import OrderedDict
import re
import json

from flask import request, abort, url_for, render_template, flash, g
from flask.ext.login import login_required
from sqlalchemy import exists, and_
from flask.ext.databrowser import ModelView
from flask.ext.databrowser.action import DeleteAction, BaseAction
from flask.ext.databrowser.column_spec import (InputColumnSpec, ColumnSpec,
                                               PlaceHolderColumnSpec, ListColumnSpec,
                                               TableColumnSpec, ImageColumnSpec, LinkColumnSpec)

from flask.ext.principal import PermissionDenied
from werkzeug.utils import redirect
from wtforms import Form, IntegerField, validators

from litefac.portal.cargo import cargo_page, fsm, gr_page
from litefac.utilities import decorators, get_or_404
from litefac.permissions import CargoClerkPermission,AdminPermission
from litefac.basemain import nav_bar
import litefac.constants.cargo as cargo_const
from litefac.database import db
from litefac.models import (UnloadSession, Plate, GoodsReceipt,
                             GoodsReceiptEntry, Product, UnloadTask, DeliverySession)
from litefac.apis.cargo import UnloadSessionWrapper, UnloadTaskWrapper, GoodsReceiptWrapper, GoodsReceiptEntryWrapper

@cargo_page.route('/')
def index():
    return redirect(unload_session_model_view.url_for_list())

@gr_page.route('/')
def index():
    return redirect(goods_receipt_model_view.url_for_list(order_by="create_time", desc=1))


class UnloadSessionModelView(ModelView):

    list_template = "cargo/unload-session-list.html"
    edit_template = "cargo/unload-session.html"

    can_batchly_edit = False

    def try_edit(self, objs=None):
        CargoClerkPermission.test()

        def _try_edit(obj_):
            if obj_ and obj_.finish_time:
                raise PermissionDenied

        if isinstance(objs, (list, tuple)):
            for obj_ in objs:
                _try_edit(obj_)
        else:
            _try_edit(objs)

    def repr_obj(self, obj):
        return unicode(obj) + "(" + cargo_const.desc_status(obj.status) + ")" + "<br /><p class='text-center'><small class='muted'>" + '&nbsp;' + ",".join([unicode(customer) for customer in obj.customer_list]) + "</small></p>"

    def get_list_columns(self):
        def gr_item_formatter(v, obj):
            # 格式化每个收货单，未打印或者过期，需要提示出来
            ret = unicode(v)
            v = GoodsReceiptWrapper(v)
            if not v.printed:
                ret += u'<small class="text-error"> (未打印)</small>'
            if v.stale:
                ret += u'<small class="text-error"> (过期)</small>'
            return ret
        return ["id", "plate_", "create_time", "finish_time", "with_person", "status",
                ListColumnSpec("customer_list_unwrapped", label=u"客 户", compressed=True),
                ListColumnSpec("goods_receipt_list_unwrapped",
                               label=u"收货单",
                               compressed=True,
                               item_col_spec=ColumnSpec("", formatter=gr_item_formatter)),
               ]

    __column_labels__ = {"id": u"编号", "plate_": u"车辆", "create_time": u"创建时间", "finish_time": u"结束时间",
                         "with_person": u"驾驶室", "status": u"状态", "goods_receipt_list": u"收货单", "gross_weight": u"净重"}

    def patch_row_attr(self, idx, obj):
        test = len(obj.customer_list) > len(obj.goods_receipt_list)
        stale = False
        unprinted = False
        for gr in obj.goods_receipt_list:
            if not gr.printed:
                unprinted = True
            if gr.stale:
                stale = True
        if test or stale:
            return {
                "title": u"有客户收货单没有生成，或者存在已经过期的收货单, 强烈建议您重新生成收货单!",
                "class": "alert alert-error"}
        elif unprinted:
            return {
                "title": u"有客户收货单没有打印",
                "class": "alert alert-warning"}

    __column_formatters__ = {
        "create_time": lambda v, obj: v.strftime("%m月%d日 %H点").decode("utf-8"),
        "finish_time": lambda v, obj: v.strftime("%m月%d日 %H点").decode("utf-8") if v else "--",
        "with_person": lambda v, obj: u'有人' if v else u'无人',
        "status": lambda v, obj: cargo_const.desc_status(v),
    }

    __default_order__ = ("id", "desc")

    __sortable_columns__ = ["id", "plate", "create_time", "finish_time"]

    from flask.ext.databrowser import filters
    from datetime import datetime, timedelta
    today = datetime.today()
    yesterday = today.date()
    week_ago = (today - timedelta(days=7)).date()
    _30days_ago = (today - timedelta(days=30)).date()

    __column_filters__ = [filters.BiggerThan("create_time", name=u"在", default_value=str(yesterday),
                                             options=[(yesterday, u'一天内'), (week_ago, u'一周内'), (_30days_ago, u'30天内')]),
                          filters.EqualTo("plate_", name=u"是"),
                          filters.Only("status", display_col_name=u"仅展示未完成会话", test=lambda col: ~col.in_([cargo_const.STATUS_CLOSED, cargo_const.STATUS_DISMISSED]), notation="__only_unclosed"),
                         ]

    def try_view(self, processed_objs=None):
        from flask.ext.principal import Permission
        Permission.union(CargoClerkPermission, AdminPermission).test()

    def preprocess(self, model):
        return UnloadSessionWrapper(model)

    def get_customized_actions(self, model_list=None):
        from litefac.portal.cargo.actions import (CloseAction, OpenAction,
                                                   CreateReceiptAction,
                                                   DeleteUnloadSessionAction)
        class _PrintGoodsReceipt(BaseAction):
            def op_upon_list(self, objs, model_list):
                obj = objs[0]
                return redirect(url_for("goods_receipt.goods_receipts_batch_print", id_=",".join([str(gr.id) for gr in obj.goods_receipt_list]), url=request.url))

        action_list = []
        if model_list is None: # for list
            action_list.extend([CloseAction(u"关闭"), OpenAction(u"打开"), CreateReceiptAction(u"生成收货单"), DeleteUnloadSessionAction(u"删除", None)])
        else:
            if len(model_list) ==1:
                if model_list[0].status in [cargo_const.STATUS_CLOSED, cargo_const.STATUS_DISMISSED]:
                    action_list.append(OpenAction(u"打开"))
                else:
                    action_list.append(CloseAction(u"关闭"))
                action_list.append(CreateReceiptAction(u"生成收货单"))
                if model_list[0].goods_receipt_list:
                    action_list.append(_PrintGoodsReceipt(u"打印收货单"))
        return action_list

    def get_list_help(self):
        return render_template("cargo/us-list-help.html")

    # ================= FORM PART ============================
    def get_create_columns(self):
        def filter_plate(q):
            return q.filter(
                and_(~exists().where(UnloadSession.plate == Plate.name).where(UnloadSession.finish_time == None),
                     ~exists().where(DeliverySession.finish_time == None).where(DeliverySession.plate == Plate.name)))

        return [InputColumnSpec("plate_",filter_=filter_plate),
                InputColumnSpec("with_person", label=u"驾驶室是否有人"),
                "gross_weight"]

    def edit_hint_message(self,obj, read_only=False):
        if read_only:
            return u"已关闭的卸货会话不能修改"
        else:
            return super(UnloadSessionModelView, self).edit_hint_message(obj, read_only)

    __form_columns__ = OrderedDict()
    __form_columns__[u"详细信息"] = [
        "plate_",
        InputColumnSpec("gross_weight", label=u"毛重"),
        InputColumnSpec("with_person", label=u"驾驶室是否有人"),
        ColumnSpec("status", label=u"状态", formatter=lambda v, obj: '<strong>' + cargo_const.desc_status(v) + '</strong>',
                   css_class="uneditable-input"),
        InputColumnSpec("create_time", label=u"创建时间", read_only=True),
        InputColumnSpec("finish_time", label=u"结束时间", read_only=True),
        PlaceHolderColumnSpec(col_name="log_list", label=u"日志", template_fname="cargo/us-log-snippet.html")
    ]
    __form_columns__[u"收货任务列表"] = [
        PlaceHolderColumnSpec(col_name="task_list", label=u"",
                              template_fname="cargo/unload-task-list-snippet.html")]
    __form_columns__[u"收货单列表"] = [PlaceHolderColumnSpec(col_name="goods_receipt_list", label=u"", template_fname="cargo/gr-list-snippet.html")]

    def get_edit_help(self, objs):
        return render_template("cargo/us-edit-help.html")

    def get_create_help(self):
        return render_template("cargo/us-create-help.html")

unload_session_model_view = UnloadSessionModelView(UnloadSession, u"卸货会话")

class plateModelView(ModelView):

    can_edit = False
    create_template = "cargo/plate.html"

    __create_columns__ = __form_columns__ = [
        InputColumnSpec("name",
                        doc=u'车牌号的形式应当是"省份缩写+字母+空格+五位数字或字母"',
                        validators=[validators.Regexp(u'^[\u4E00-\u9FA3][a-z]\s*[a-z0-9]{5}$', flags=re.IGNORECASE|re.U, message=u"格式错误")]),
    ]

    def populate_obj(self, form):
        # normalize plate
        name = form["name"].data
        m = re.match(u'^(?P<part1>[\u4E00-\u9FA3][a-z])\s*(?P<part2>[a-z0-9]{5})$', name, re.IGNORECASE|re.U)
        name = m.groupdict()["part1"] + ' ' + m.groupdict()["part2"]
        name = name.upper()
        return Plate(name=name)

plate_model_view = plateModelView(Plate, u"车辆")

class GoodsReceiptEntryModelView(ModelView):

    @login_required
    def try_view(self, processed_objs=None):
        pass

    __form_columns__ = [
        InputColumnSpec("product", group_by=Product.product_type, label=u"产品",
                        filter_=lambda q: q.filter(Product.enabled==True)),
        InputColumnSpec("goods_receipt", label=u"收货单", read_only=True),
        InputColumnSpec("weight", label=u"重量"),
        InputColumnSpec("harbor", label=u"装卸点"),
        ImageColumnSpec("pic_url", label=u"图片")]

    def preprocess(self, obj):
        return GoodsReceiptEntryWrapper(obj)

    def try_edit(self, objs=None):
        # 若收货单已经生成了订单，或者收货单已经过时，那么不能进行修改
        def _try_edit(obj):
            if obj:
                if isinstance(obj, self.data_browser.db.Model):
                    obj = GoodsReceiptEntryWrapper(obj)
                if obj.goods_receipt.stale or obj.goods_receipt.order:
                    raise PermissionDenied
        CargoClerkPermission.test()

        if isinstance(objs, list) or isinstance(objs, tuple):
            return any(_try_edit(obj) for obj in objs)
        else:
            return _try_edit(objs)

    def edit_hint_message(self, obj, read_only=False):
        if read_only:
            if obj.goods_receipt.stale:
                return u"收货单过时，不能修改"
            elif obj.goods_receipt.order:
                return u"收货单已生成订单，不能修改"
            else:
                return u""
        else:
            return super(GoodsReceiptEntryModelView, self).edit_hint_message(obj, read_only)

goods_receipt_entry_view = GoodsReceiptEntryModelView(GoodsReceiptEntry, u"收货单产品")

@cargo_page.route("/weigh-unload-task/<int:id_>", methods=["GET", "POST"])
@decorators.templated("/cargo/unload-task.html")
def weigh_unload_task(id_):
    from litefac import apis
    from litefac.apis import todo
    task = apis.cargo.get_unload_task(id_)
    if not task:
        abort(404)
    if request.method == 'GET':
        return dict(plate=task.unload_session.plate, task=task,
                    product_types=apis.product.get_product_types(),
                    products=json.dumps(apis.product.get_products()),
                    customers=apis.customer.get_customer_list(),
                    titlename=u"收货任务")
    else:  # POST
        class _ValidationForm(Form):
            weight = IntegerField('weight', [validators.required()])
            customer = IntegerField('customer', [validators.required()])
            product = IntegerField('product')
        form = _ValidationForm(request.form)
        if form.validate():
            customer = apis.customer.get_customer(form.customer.data)
            weight = task.last_weight - form.weight.data
            if weight < 0 or not customer:
                abort(403)
            task.update(weight=weight, product_id=form.product.data, customer=customer)
            from flask.ext.login import current_user
            fsm.fsm.reset_obj(task.unload_session)
            fsm.fsm.next(cargo_const.ACT_WEIGHT, current_user)
            todo.remove_todo(todo.WEIGH_UNLOAD_TASK, id_)
            return redirect(
                request.form.get("url", unload_session_model_view.url_for_object(model=task.unload_session.model)))
        else:
            if request.form.get("method") == "delete":
                if task.delete():
                    flash(u"删除卸货任务%d成功" % task.id)
                    return redirect(request.form.get("url", unload_session_model_view.url_for_object(
                        model=task.unload_session.model)))
            return render_template("validation-error.html", errors=form.errors,
                                   back_url=unload_session_model_view.url_for_object(model=task.unload_session.model),
                                   nav_bar=nav_bar), 403

class UnloadTaskModelView(ModelView):
    edit_template = "cargo/unload-task-spinnet.html"

    create_in_steps = True

    step_create_templates = [None, None, None, 'cargo/unload-task-pic.html', None]

    __create_columns__ = OrderedDict()
    __create_columns__[u"选择车辆"] = [
        PlaceHolderColumnSpec("unload_session", filter_=lambda q: q.filter(UnloadSession.finish_time == None),
                              template_fname="cargo/unload-task-plate.html", as_input=True, label="")]

    __create_columns__[u"选择卸货点"] = [
        PlaceHolderColumnSpec("harbor", template_fname="cargo/unload-task-harbor.html", as_input=True, label="")]

    __create_columns__[u"选择客户"] = [InputColumnSpec("customer", label="")]


    __create_columns__[u"拍照"] = [PlaceHolderColumnSpec("pic_path", template_fname="cargo/unload-task-pic.html", as_input=True, label="")]

    __create_columns__[u"是否完全卸货"] = [PlaceHolderColumnSpec("is_finished", template_fname="cargo/unload-task-finished.html")]

    __form_columns__ = [
        ColumnSpec("id", label=u"编号"),
        ColumnSpec("customer", label=u"客户"),
        InputColumnSpec("product", group_by=Product.product_type, label=u"产品",
                        filter_=lambda q: q.filter(Product.enabled == True)),
        InputColumnSpec("weight", label=u"重量"),
        InputColumnSpec("harbor", label=u"装卸点"),
        PlaceHolderColumnSpec(col_name="pic_url", label=u"图片", template_fname="pic-snippet.html")]

    def preprocess(self, obj):
        return UnloadTaskWrapper(obj)

    def try_edit(self, objs=None):
        CargoClerkPermission.test()

        if any(obj.unload_session.status==cargo_const.STATUS_CLOSED for obj in objs):
            raise PermissionDenied

    def edit_hint_message(self, objs, read_only=False):
        if read_only:
            return u"本卸货会话已经关闭，所以不能修改卸货任务"
        return super(UnloadTaskModelView, self).edit_hint_message(objs, read_only)

    @login_required
    def try_view(self, processed_objs=None):
        pass

unload_task_model_view = UnloadTaskModelView(UnloadTask, u"卸货任务")

class GoodsReceiptModelView(ModelView):

    edit_template = "cargo/goods-receipt.html"

    can_batchly_edit = True

    __default_order__ = ("create_time", "desc")
    def try_create(self):
        raise PermissionDenied

    def preprocess(self, obj):
        return GoodsReceiptWrapper(obj)

    @login_required
    def try_view(self, processed_objs=None):
        pass

    __sortable_columns__ = ["id", "create_time"]

    __list_columns__ = ["id", "receipt_id", "customer", "unload_session.plate", InputColumnSpec("order", formatter=lambda v, obj: v or "--", label=u"订单"),
                        ColumnSpec("printed", formatter=lambda v, obj: u"是" if v else u"否", label=u"是否打印"),
                        ColumnSpec("stale", formatter=lambda v, obj: u"是" if v else u"否", label=u"是否过时"),
                        ColumnSpec("create_time", formatter=lambda v, obj: v.strftime("%y年%m月%d日 %H时%M分").decode("utf-8"), label=u"创建时间"), ColumnSpec("creator"),
                        ListColumnSpec("goods_receipt_entries", label=u"产品", compressed=True,
                                       item_col_spec=ColumnSpec("", formatter=lambda v, obj: unicode(v.product.product_type) + u"-" + unicode(v.product)))]

    def patch_row_attr(self, idx, obj):
        if obj.stale:
            return {
                "class": "alert alert-error",
                "title": u"本收货单已经过时，请回到卸货会话重新生成"
            }
        if not obj.printed:
            return {
                "class": "alert alert-warning",
                "title": u"本收货单尚未打印"
            }

    from flask.ext.databrowser import filters
    from datetime import datetime, timedelta
    today = datetime.today()
    yesterday = today.date()
    week_ago = (today - timedelta(days=7)).date()
    _30days_ago = (today - timedelta(days=30)).date()

    class NoneOrder(filters.Only):
        def set_sa_criterion(self, q):
            if self.value:
                return q.filter(GoodsReceipt.order == None)
            else:
                return q

    __column_filters__ = [filters.BiggerThan("create_time", name=u"在", default_value=str(yesterday),
                                             options=[(yesterday, u'一天内'), (week_ago, u'一周内'), (_30days_ago, u'30天内')]),
                          filters.EqualTo("customer", name=u"是"),
                          filters.Only("printed", display_col_name=u"仅展示未打印收货单", test=lambda col: ~col, notation="__only_unprinted"),
                          NoneOrder("order", display_col_name=u"仅展示未生成订单", test=None, notation="__none")
                         ]

    __form_columns__ = OrderedDict()
    __form_columns__[u"详细信息"] = [
        "receipt_id",
        "customer",
        "unload_session.plate",
        ColumnSpec("create_time", label=u"创建时间"),
        ColumnSpec("creator"),
        ColumnSpec("printed", label=u"是否打印",
                        formatter=lambda v, obj: u"是" if v else u'<span class="text-error">否</span>'),
        ColumnSpec("stale", label=u"是否过时",
                  formatter=lambda v, obj: u'<span class="text-error">是</span>' if v else u"否"),
        PlaceHolderColumnSpec("log_list", label=u"日志", template_fname="cargo/gr-logs-snippet.html")
    ]
    __form_columns__[u"产品列表"] = [
        TableColumnSpec("goods_receipt_entries", label="",
                        col_specs=[
                            LinkColumnSpec("id", label=u"编号",
                                           formatter=lambda v, obj: goods_receipt_entry_view.url_for_object(obj,url=request.url), anchor=lambda v:v),
                            ColumnSpec("product", label=u"产品"),
                            ColumnSpec("product.product_type", label=u"产品类型"),
                            ColumnSpec("weight", label=u"净重(KG)"),
                            PlaceHolderColumnSpec(col_name="pic_url", label=u"图片",
                                                  template_fname="cargo/pic-snippet.html")],
                        preprocess=lambda obj: GoodsReceiptWrapper(obj))
    ]
    __column_labels__ = {"receipt_id": u'编 号', "customer": u'客 户', "unload_session.plate": u"车牌号",
                         "printed": u'是否打印', "stale": u"是否过时", "create_time": u"创建时间", "order": u"订 单",
                         "creator": u"创建者"}

    def get_customized_actions(self, objs=None):
        from litefac.portal.cargo.actions import PrintGoodsReceipt, BatchPrintGoodsReceipt, CreateOrderAction, \
            CreateExtraOrderAction, ViewOrderAction, DeleteGoodsReceiptAction
        delete_goods_receipt_action = DeleteGoodsReceiptAction(u"删除")
        if not objs:
            if g.request_from_mobile:
                return [delete_goods_receipt_action]
            else:
                return [BatchPrintGoodsReceipt(u"批量打印"), delete_goods_receipt_action]
        else:
            def _l(obj):
                if obj.order:
                    return [ViewOrderAction(u"查看订单")]
                else:
                    l = [CreateOrderAction(u"生成计重类型订单"), CreateExtraOrderAction(u"生成计件类型订单")]
                    if not obj.printed:
                        l.append(delete_goods_receipt_action)
                    return l

            if isinstance(objs, (list, tuple)):
                if len(objs) == 1:
                    l = _l(objs[0])
                else:
                    l = []
            else:
                l = _l(objs)
            if not g.request_from_mobile:
                l.append(PrintGoodsReceipt(u"打印"))
            return l

    def try_edit(self, objs=None):
        def _try_edit(obj):
            if obj:
                if isinstance(obj, self.data_browser.db.Model):
                    obj = self.preprocess(obj)
                if obj.stale or obj.order:
                    raise PermissionDenied
        CargoClerkPermission.test()

        if isinstance(objs, list) or isinstance(objs, tuple):
            return any(_try_edit(obj) for obj in objs)
        else:
            return _try_edit(objs)

    def edit_hint_message(self,obj, read_only=False):
        if read_only:
            if obj.order:
                return u"已生成订单的收货单不能修改"
            else:
                return u"已过时的收货单不能修改"
        else:
            return super(GoodsReceiptModelView, self).edit_hint_message(obj, read_only)

    def batch_edit_hint_message(self, objs, read_only=False):
        if read_only:
            obj_ids = ",".join([obj.receipt_id for obj in objs])
            for obj in objs:
                if obj.order:
                    return u"收货单%s已生成订单，不能批量修改%s" % (obj.receipt_id, obj_ids)
                elif obj.stale:
                    return u"收货单%s已过时，不能批量修改%s" % (obj.receipt_id, obj_ids)
            else:
                return u"存在不能修改的收货单"
        else:
            return super(GoodsReceiptModelView, self).edit_hint_message(objs, read_only)

    def get_batch_form_columns(self, preprocessed_objs=None):
        return ["customer", "receipt_id", "create_time", "printed"]

goods_receipt_model_view = GoodsReceiptModelView(GoodsReceipt, u"收货单")

@cargo_page.route("/goods-receipt-preview/<int:id_>")
@decorators.templated("cargo/goods-receipt-preview.html")
@decorators.nav_bar_set
def goods_receipt_preview(id_):
    from litefac import apis

    receipt = apis.cargo.get_goods_receipt(id_)
    PER_PAGE  = apis.config.get("print_count_per_page", 5.0, type=float)
    import math
    pages = int(math.ceil(len(receipt.goods_receipt_entries) / PER_PAGE))
    if not receipt:
        abort(404)
    return {"receipt": receipt, "titlename": u"收货单打印预览", "pages": pages,
            "per_page": PER_PAGE}

def refresh_gr(id_):
    from litefac import apis

    receipt = apis.cargo.get_goods_receipt(id_)

    if not receipt:
        abort(404)
    if not receipt.stale:
        return render_template("error.html", msg=u"收货单%d未过时，不需要更新" % id_), 403
    else:
        receipt.add_product_entries()
        return redirect(request.args.get("url") or url_for("goods_receipt.goods_receipt", id_=id_))

@gr_page.route("/goods-receipts-batch-print/<id_>")
@decorators.templated("cargo/goods-receipts-batch-print.html")
@decorators.nav_bar_set
def goods_receipts_batch_print(id_):
    from litefac import apis
    per_page  = apis.config.get("print_count_per_page", 5, type=int)
    gr_list = [get_or_404(GoodsReceipt, i) for i in id_.split(",")]
    pages = 0
    for gr in gr_list:
        gr.printed = True
        import math
        pages += int(math.ceil(len(gr.unload_task_list) / per_page))
    db.session.commit()
    return {"gr_list": gr_list, "titlename":u"批量打印",
            "per_page": per_page, "pages": pages, "back_url": request.args.get("url", "/")}

