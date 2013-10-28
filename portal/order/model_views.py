# -*- coding: UTF-8 -*-
from collections import OrderedDict
from flask import url_for, request
from flask.ext.login import login_required
from flask.ext.principal import PermissionDenied, Permission
from flask.ext.databrowser import ModelView, filters
from flask.ext.databrowser.column_spec import (InputColumnSpec, LinkColumnSpec, ColumnSpec, TableColumnSpec, ImageColumnSpec, PlaceHolderColumnSpec)

from wtforms import validators

from litefac import constants
from litefac.permissions import SchedulerPermission, CargoClerkPermission
from litefac.models import Order, SubOrder, Product
from litefac.portal.order.filters import category_filter, only_unfinished_filter


class OrderModelView(ModelView):
    list_template = "order/order-list.html"
    edit_template = "order/order.html"
    def try_create(self):
        raise PermissionDenied

    can_batchly_edit = False

    @login_required
    def try_view(self, processed_objs=None):
        pass


    def __list_filters__(self):
        if SchedulerPermission.can():
            return [filters.EqualTo("finish_time", value=None),
                    filters.EqualTo("refined", value=True),
                    filters.EqualTo("dispatched", value=True),
                    only_unfinished_filter
                    ]
        else:
            return []

    __list_columns__ = ["id", "customer_order_number", "goods_receipt.customer", "net_weight", "remaining_weight",
                        PlaceHolderColumnSpec(col_name="manufacturing_work_command_list", label=u"生产中重量",
                                              template_fname="order/todo-work-command-list-snippet.html",
                                              doc=u"若大于0,请敦促车间生产"),
                        PlaceHolderColumnSpec(col_name="qi_work_command_list", label=u"待质检重量",
                                              template_fname="order/qi-list-snippet.html"),
                        PlaceHolderColumnSpec(col_name="done_work_command_list", label=u"已完成重量",
                                              template_fname="order/done-work-command-list-snippet.html",
                                              doc=u"指订单下所有是最后一道工序的工单,这类工单的工序后质量之和"),
                        PlaceHolderColumnSpec(col_name="to_deliver_store_bill_list", label=u"待发货重量",
                                              template_fname="order/store-bill-list-snippet.html"),
                        "delivered_weight", "create_time", "dispatched_time", "goods_receipt",
                        ColumnSpec("urgent", formatter=lambda v,obj:u"<span class='text-error'>是</span>" if v else u"否"),
                        "refined"]

    def repr_obj(self, obj):
        return unicode(obj) + "<br /><p class='text-center'><small class='muted'>" + unicode(
            obj.goods_receipt.customer) + "</small></p>"

    __sortable_columns__ = ["id", "customer_order_number", "goods_receipt.customer", "create_time", "goods_receipt"]

    __column_labels__ = {"customer_order_number": u"订单号", "goods_receipt.customer": u"客户", "create_time": u"创建时间",
                         "goods_receipt": u"收货单", "net_weight": u"收货重量", "remaining_weight": u"待调度重量",
                         "delivered_weight": u"已发货重量", "refined": u"完善", "urgent": u"加急","product":u"产品",
                         "category": u"类型", "dispatched_time": u"下发时间"}

    __column_docs__ = {"remaining_weight": u"若大于0,请敦促调度员排产"}

    __column_formatters__ = {"urgent": lambda v, obj: u"是" if v else u"否",
                             "customer_order_number": lambda v, obj: (
                                                                         "" if not obj.warning else '<i class="icon-exclamation-sign"></i>') + v + (u"<b>(退货)</b>" if any(so.returned for so in
                                                                                               obj.sub_order_list) else ""),
                             "remaining_weight": lambda v, obj: unicode(v + obj.to_work_weight),
                             "refined": lambda v, obj: u"是" if v else u"否",
                             "create_time": lambda v, obj: v.strftime("%m-%d %H") + u"点",
                             "dispatched_time": lambda v, obj: v.strftime("%m-%d %H") + u"点" if v else "",
    }

    def get_column_filters(self):
        from datetime import datetime, timedelta
        today = datetime.today()
        yesterday = today.date()
        week_ago = (today - timedelta(days=7)).date()
        _30days_ago = (today - timedelta(days=30)).date()
        ret =  [filters.EqualTo("goods_receipt.customer", name=u"是"), filters.BiggerThan("create_time", name=u"在",
                        options=[(yesterday, u'一天内'), (week_ago, u'一周内'),
                        (_30days_ago, u'30天内')]), category_filter]
        if not SchedulerPermission.can():
            ret.append(only_unfinished_filter)
        return ret

    def preprocess(self, model):
        from litefac.apis.order import OrderWrapper
        return OrderWrapper(model)



    def get_customized_actions(self, processed_objs=None):
        __customized_actions__ = []
        if CargoClerkPermission.can():
            from litefac.portal.order.actions import dispatch_action, mark_refined_action, account_action, new_extra_order_action
            if processed_objs:
                if not processed_objs[0].refined:
                    __customized_actions__.append(mark_refined_action)
                    if not processed_objs[0].dispatched and not processed_objs[0].measured_by_weight:
                        __customized_actions__.append(new_extra_order_action)
                elif not processed_objs[0].dispatched:
                    __customized_actions__.append(dispatch_action)
                if processed_objs[0].can_account:
                    __customized_actions__.append(account_action)
            else:
                __customized_actions__ = [dispatch_action, mark_refined_action, account_action]
        return __customized_actions__

    def patch_row_attr(self, idx, row):
        if not row.refined:
            return {"class": "alert alert-warning", "title": u"此订单没有完善，请先完善订单"}
        elif row.urgent and row.remaining_quantity:
            return {"class": "alert alert-error", "title": u"此订单请加急完成"}
        elif row.warning:
            return {"title": u"此订单的收货重量大于未分配重量，生产中重量，已发货重量，待发货重量之和"}

    def url_for_object(self, model, **kwargs):
        if model:
            return url_for("order.order", id_=model.id, **kwargs)
        else:
            return url_for("order.order", **kwargs)

    __default_order__ = ("id", "desc")

    def get_form_columns(self, obj=None):
        form_columns = OrderedDict()
        form_columns[u"订单详情"] = ["customer_order_number", ColumnSpec("goods_receipt.customer"),
                                 ColumnSpec("goods_receipt", css_class="control-text", label=u"收货单"), "net_weight",
                                 ColumnSpec("create_time"), ColumnSpec("dispatched_time"),
                                 PlaceHolderColumnSpec("log_list", label=u"日志", template_fname="logs-snippet.html")]
        form_columns[u"子订单列表"] = [PlaceHolderColumnSpec("sub_order_list", template_fname="order/sub-order-list-snippet.html", label="")]
        if SchedulerPermission.can():
            from litefac.portal.manufacture.views import work_command_view

            form_columns[u"工单列表"] = [TableColumnSpec("work_command_list", label="", col_specs=[
                LinkColumnSpec("id", label=u"编号", anchor=lambda v: v,
                               formatter=lambda v, obj: work_command_view.url_for_object(obj, url=request.url)),
                ColumnSpec("sub_order.id", label=u"子订单编号"), ColumnSpec("product", label=u"产品名称"),
                ColumnSpec("urgent", label=u"加急", formatter=lambda v,obj: u"<span class='text-error'>是</span>" if v else u"否"),
                ColumnSpec("sub_order.returned", label=u"退镀", formatter=lambda v,obj: u"<span class='text-error'>是</span>" if v else u"否"),
                ColumnSpec("org_weight", label=u"工序前重量"), ColumnSpec("org_cnt", label=u"工序前数量"),
                ColumnSpec("unit", label=u"单位"), ColumnSpec("processed_weight", label=u"工序后重量"),
                ColumnSpec("processed_cnt", label=u"工序后数量"),ColumnSpec("tech_req", label=u"技术要求"),
                ColumnSpec("department", label=u"车间"), ColumnSpec("team", label=u"班组"),
                ColumnSpec("qi", label=u"质检员"), ColumnSpec("status_name", label=u"状态")])]
        form_columns[u'订单流程图'] = [PlaceHolderColumnSpec('work_flow_json', template_fname='order/order-work-flow-snippet.html', label='')]
        return form_columns


    def try_edit(self, processed_objs=None):
        Permission.union(SchedulerPermission, CargoClerkPermission).test()
        if processed_objs and processed_objs[0].refined or processed_objs[0].dispatched:
            raise PermissionDenied

    def edit_hint_message(self,obj, read_only=False):
        if read_only:
            if SchedulerPermission.can():
                return u"正在排产订单%s" % obj.customer_order_number
            else:
                if obj.refined:
                    return u"订单%s已标记完善，不能修改" % obj.customer_order_number
                if obj.refined:
                    return u"订单%s已下发，不能修改" % obj.customer_order_number
                return ""
        else:
            return super(OrderModelView, self).edit_hint_message(obj, read_only)

class SubOrderModelView(ModelView):
    """

    """
    can_batchly_edit = False

    edit_template = "order/sub-order.html"

    def try_edit(self, processed_objs=None):
        Permission.union(SchedulerPermission, CargoClerkPermission).test()

        if processed_objs:
            if processed_objs[0].order.refined or processed_objs[0].order.dispatched:
                raise PermissionDenied

    @login_required
    def try_view(self, processed_objs=None):
        pass

    def edit_hint_message(self,obj, read_only=False):
        if read_only:
            if obj.order.refined:
                return u"子订单%s已标记完善，不能修改" % obj.id
            if obj.order.dispatched:
                return u"子订单%s已下发，不能修改" % obj.id
        else:
            return super(SubOrderModelView, self).edit_hint_message(obj, read_only)

    def get_form_columns(self, obj=None):

        form_columns = [ColumnSpec("id", label=u"编号"),
                        InputColumnSpec("product", group_by=Product.product_type),
                        "weight", ColumnSpec("harbor"), "urgent", "returned", "tech_req",
                        InputColumnSpec("due_time", validators=[validators.Required(message=u"该字段不能为空")])]
        if obj and obj.order_type == constants.EXTRA_ORDER_TYPE:
            form_columns.extend(["spec", "type", "quantity", "unit"])
        form_columns.extend([ColumnSpec("create_time"), ImageColumnSpec("pic_url", label=u"图片"),
                        PlaceHolderColumnSpec("log_list", label=u"日志", template_fname="logs-snippet.html")])
        return form_columns

    __column_labels__ = {"product": u"产品", "weight": u"重量", "harbor": u"卸货点", "urgent": u"加急", "returned": u"退镀",
                         "tech_req": u"技术要求", "create_time": u"创建时间", "due_time": u"交货日期", "quantity": u"数量",
                         "unit": u"数量单位", "type": u"型号", "spec": u"规格"}

    def preprocess(self, obj):
        from litefac.apis.order import SubOrderWrapper
        return SubOrderWrapper(obj)

    def on_model_change(self, form, model):
        if model.order_type == constants.STANDARD_ORDER_TYPE:
            model.quantity = model.weight
        model.remaining_quantity = model.quantity

from nav_bar import NavBar

order_model_view = OrderModelView(Order, u"订单")
sub_order_model_view = SubOrderModelView(SubOrder, u"子订单")
sub_nav_bar = NavBar()
sub_nav_bar.register(lambda: order_model_view.url_for_list(order_by="id", desc="1", category=""), u"所有订单",
                     enabler=lambda: category_filter.unfiltered(request.args.get("category", None)))
sub_nav_bar.register(
    lambda: order_model_view.url_for_list(order_by="id", desc="1", category=str(category_filter.UNDISPATCHED_ONLY)),
    u"仅展示待下发订单", enabler=lambda: request.args.get("category", "") == str(category_filter.UNDISPATCHED_ONLY))
sub_nav_bar.register(
    lambda: order_model_view.url_for_list(order_by="id", desc="1", category=category_filter.DELIVERABLE_ONLY),
    u"仅展示可发货订单", enabler=lambda: request.args.get("category", "") == str(category_filter.DELIVERABLE_ONLY))
sub_nav_bar.register(
    lambda: order_model_view.url_for_list(order_by="id", desc="1", category=category_filter.ACCOUNTABLE_ONLY),
    u"仅展示可盘点订单", enabler=lambda: request.args.get("category", "") == str(category_filter.ACCOUNTABLE_ONLY))


def hint_message(model_view):
    filter_ = [filter_ for filter_ in model_view.parse_filters() if filter_.col_name == "category"][0]
    if not filter_.has_value():
        return ""
    filter_.value = int(filter_.value)

    if filter_.value == category_filter.UNDISPATCHED_ONLY:
        return u"未下发订单未经收发员下发，调度员不能排产，请敦促收发员完善订单并下发"
    elif filter_.value == category_filter.DELIVERABLE_ONLY:
        return u"可发货订单中全部或部分产品可以发货，注意请催促质检员及时打印仓单"
    elif filter_.value == category_filter.ACCOUNTABLE_ONLY:
        return u"可盘点订单已经生产完毕（指已经全部分配给车间生产，最终生产完成，并通过质检），但是仍然有部分仓单没有发货。盘点后，这部分仓单会自动关闭"
    return ""
