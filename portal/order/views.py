# -*- coding: utf-8 -*-
"""
@author: Yangminghua
"""
from datetime import date
from flask import request, url_for, render_template, abort, flash, redirect, json
from flask.ext.login import current_user
from wtforms import Form, TextField, IntegerField, validators, BooleanField, DateField, HiddenField
from litefac.portal.order import order_page
from litefac.utilities import decorators


@order_page.route("/new-sub-order", methods=["GET", "POST"])
@decorators.templated("/order/new-extra-sub-order.html")
@decorators.nav_bar_set
def new_sub_order():
    """
    创建新的计件类型的子订单（只有计件类型的订单能够增加子订单）
    """
    from litefac import apis

    if request.method == "GET":
        from litefac import apis

        order = apis.order.get_order(request.args.get("order_id", type=int))
        if not order:
            abort(404)
        if order.dispatched or order.refined:
            return render_template("result.html",
                                   error_content=u"已下发或已标记完善的订单不能新增子订单",
                                   back_url=url_for("order.order",
                                                    id=order.id))
        from litefac.constants import DEFAULT_PRODUCT_NAME

        return dict(titlename=u'新建子订单', order=order,
                    DEFAULT_PRODUCT_NAME=DEFAULT_PRODUCT_NAME,
                    product_types=apis.product.get_product_types(),
                    products=json.dumps(apis.product.get_products()),
                    harbor_list=apis.harbor.get_harbor_list(),
                    team_list=apis.manufacture.get_team_list())
    else:
        class NewSubOrderForm(Form):
            order_id = IntegerField('order_id', [validators.required()])
            product = IntegerField('product', [validators.required()])
            spec = TextField('spec', [validators.required()])
            type = TextField('type', [validators.required()])
            tech_req = TextField('tech_req')
            due_time = DateField('due_time',
                                 [validators.required()])
            urgent = BooleanField('urgent')
            returned = BooleanField('returned')
            unit = TextField('unit')
            quantity = IntegerField('quantity')
            weight = IntegerField('weight', [validators.required()])
            harbor = TextField('harbor', [validators.required()])

        form = NewSubOrderForm(request.form)
        order_id = form.order_id.data
        due_time = form.due_time.data
        if date.today() > due_time:
            return render_template("result.html",
                                   error_content=u"错误的交货日期",
                                   back_url=url_for("order.order",
                                                    id_=order_id))
        from litefac import apis

        try:
            sb = apis.order.SubOrderWrapper.new_sub_order(order_id=order_id, product_id=form.product.data,
                                                          spec=form.spec.data, type=form.type.data,
                                                          tech_req=form.tech_req.data, due_time=str(due_time),
                                                          urgent=form.urgent.data, weight=form.weight.data,
                                                          harbor_name=form.harbor.data, returned=form.returned.data,
                                                          unit=form.unit.data, quantity=form.quantity.data)
            flash(u"新建成功！")
        except ValueError, e:
            flash(unicode(e), "error")
        return redirect(url_for('order.order', id_=order_id))

@order_page.route('/work-command', methods=['GET', 'POST'])
@decorators.templated("order/work-command.html")
@decorators.nav_bar_set
def work_command():
    """
    生成一个新的工单
    """
    if request.method == "GET":
        from litefac import apis

        sub_order = apis.order.SubOrderWrapper.get_sub_order(
            request.args.get("sub_order_id", type=int))
        if not sub_order:
            abort(404)
        try:
            dep = apis.harbor.get_harbor_model(sub_order.harbor.name).department
            return dict(sub_order=sub_order, procedure_list=dep.procedure_list, department=dep, titlename=u"预排产")
        except AttributeError:
            abort(404)
    else:
        from litefac.apis import manufacture, order

        class PreScheduleForm(Form):
            sub_order_id = HiddenField('sub_order_id', [validators.required()])
            schedule_weight = IntegerField('schedule_weight',
                                           [validators.required()])
            procedure = IntegerField('procedure')
            tech_req = TextField('tech_req')
            schedule_count = IntegerField('schedule_count')
            urgent = BooleanField('urgent')
            url = HiddenField("url")

        form = PreScheduleForm(request.form)
        sub_order = order.get_sub_order(form.sub_order_id.data)
        if not sub_order:
            abort(404)
        if form.validate():
            try:
                inst = manufacture.new_work_command(
                    sub_order_id=sub_order.id,
                    org_weight=form.schedule_weight.data,
                    procedure_id=form.procedure.data,
                    org_cnt=form.schedule_count.data,
                    urgent=form.urgent.data,
                    tech_req=form.tech_req.data)
                if inst:
                    from litefac.apis.todo import remove_todo, DISPATCH_ORDER

                    remove_todo(DISPATCH_ORDER, sub_order.order.id)

                    from litefac.basemain import timeline_logger
                    timeline_logger.info(u"新建",
                                         extra={"obj": inst,
                                                "actor": current_user if current_user.is_authenticated() else None,
                                                "action": u"新建", "obj_pk": inst.id})

                    if inst.sub_order.returned:
                        flash(u"成功创建工单（编号%d），请提醒质检员赶快处理" % inst.id)
                    else:
                        flash(u"成功创建工单（编号%d）" % inst.id)
            except ValueError as a:
                return render_template("error.html", msg=a.message,
                                       back_url=form.url.data or url_for('order.order', id_=sub_order.order.id)), 403
            return redirect(form.url.data or url_for('order.order', id_=sub_order.order.id))
        else:
            return render_template("error.html", msg=form.errors,
                                   back_url=url_for('order.order', id_=sub_order.order.id)), 403
