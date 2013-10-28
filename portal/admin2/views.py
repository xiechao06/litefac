# -*- coding: UTF-8 -*-
import json
import numbers
import codecs
import csv
import cStringIO
import errno

from wtforms import Form, DateField
from flask import flash, redirect, url_for, request, render_template
from flask.ext.databrowser import ModelView, column_spec, filters
from flask.ext.databrowser.action import DeleteAction
from flask.ext.databrowser.filters import BaseFilter, Contains
from flask.ext.principal import Permission, PermissionDenied

from litefac.models import (User, Group, Department, Team, Procedure,
    Harbor, Config, Customer, Product)
import litefac.constants as constants
import litefac.constants.groups as groups_const
from litefac.permissions.roles import AdminPermission, CargoClerkPermission
from litefac.portal.admin2 import admin2_page
from litefac.basemain import nav_bar
from litefac.utilities.decorators import templated

class AdminModelView(ModelView):
    can_batchly_edit = False
    list_template = "admin2/list.html"
    create_template = edit_template = "admin2/object.html"

    def try_view(self, objs=None):
        AdminPermission.test()

    def try_edit(self, objs=None):
        AdminPermission.test()

class UserModelView(AdminModelView):

    edit_template = create_template = "admin2/user.html"
    column_hide_backrefs = False

    __list_columns__ = ["id", "username", column_spec.PlaceHolderColumnSpec("groups", label=u"用户组",
                                                                            template_fname="admin2/user-groups-snippet.html"), 'enabled']
    __column_labels__ = {"id": u"编号", "username": u"用户名", "group": u"用户组", "password": u"密码(md5加密)",
                         "groups": u"用户组列表", 'enabled': u'激活'}
    __column_formatters__ = {"enabled": lambda v, obj: u"是" if v else u"否"}

    class UserDeleteAction(DeleteAction):

        def test_enabled(self, obj):
            if obj.id == constants.ADMIN_USER_ID:
                return -2
            return 0

        def get_forbidden_msg_formats(self):
            return {
                -2: u"您不能删除超级管理员!"
            }

    def get_column_filters(self):
        class UserGroupFilter(BaseFilter):

            def set_sa_criterion(self, query):
                if isinstance(self.value, numbers.Number) or self.value.isdigit():
                    self.value = int(self.value)
                    query = query.filter(User.groups.any(Group.id==self.value))
                return query
        return [UserGroupFilter(u"group", name=u"是", options=[(group.id, group.name) for group in Group.query.all()]), Contains(u'username', name=u'包含')]

    # ============ FORM PART ===========================
    __create_columns__ = __form_columns__ = ["username", "password", "groups", 'enabled']

user_model_view = UserModelView(User, u"用户")

class CustomerModelView(AdminModelView):

    def try_view(self, objs=None):
        Permission.union(AdminPermission, CargoClerkPermission).test()

    __column_labels__ = {"id": u"编号", "name": u"名称", "abbr": u"拼音首字母简写", "enabled": u"是否激活", "MSSQL_ID": u"MsSQL数据库对应ID"}
    __column_formatters__ = {"enabled": lambda v, obj: u"是" if v else u"否"}
    __form_columns__ = [column_spec.InputColumnSpec('id', read_only=True), 'name', 'abbr', 'enabled', column_spec.InputColumnSpec('MSSQL_ID', read_only=True)]
    __batch_form_columns__ = ['enabled']
    can_batchly_edit = True

customer_model_view = CustomerModelView(Customer, u"客户")

class GroupModelView(AdminModelView):

    __list_columns__ = ["id", "name"]
    __column_labels__ = {"id": u"编号", "name": u"组名", "permissions": u"权限列表"}

    class GroupDeleteAction(DeleteAction):

        def test_enabled(self, obj):
            if obj.id in {groups_const.DEPARTMENT_LEADER,
                          groups_const.TEAM_LEADER,
                          groups_const.LOADER,
                          groups_const.QUALITY_INSPECTOR,
                          groups_const.CARGO_CLERK,
                          groups_const.SCHEDULER,
                          groups_const.ACCOUNTANT,
                          groups_const.ADMINISTRATOR}:
                return -2
            return 0

        def get_forbidden_msg_formats(self):
            return {
                -2: u"您不能删除系统内建用户组!"
            }

    __customized_actions__ = [GroupDeleteAction(u"删除", AdminPermission)]

    # ======================= FORM PART ==================================
    __form_columns__ = __create_columns__ =  ["name", "permissions"]

group_model_view = GroupModelView(Group, u"用户组")


class DepartmentModelView(AdminModelView):

    __list_columns__ = ["id", "name",
                        column_spec.PlaceHolderColumnSpec("team_list", label=u"班组列表", template_fname="admin2/department-team-list-snippet.html"),
                        column_spec.PlaceHolderColumnSpec("leader_list", label=u"车间主任", template_fname="admin2/department-leader-list-snippet.html"),
                        column_spec.PlaceHolderColumnSpec("procedure_list", label=u"允许工序", template_fname="admin2/department-procedure-list-snippet.html")]

    __create_columns__ = __form_columns__ = ["name",
                                             column_spec.InputColumnSpec("leader_list",
                                                                         label=u"车间主任列表",
                                                                         opt_filter=lambda obj: any((group.id == groups_const.DEPARTMENT_LEADER) for group in obj.groups),
                                                                         doc=u'只有用户组是"车间主任", 才能作为车间主任'),
                                             "procedure_list"]

    __column_labels__ = {"id": u"编号", "name": u"名称", "leader_list": u"车间主任列表", "procedure_list": u"车间允许工序列表"}

    __customized_actions__ = [DeleteAction(u"删除", AdminPermission)]

    def populate_obj(self, form):
        return Department(name=form.name.data, leaders=form.leader_list.data)

department_model_view = DepartmentModelView(Department, u"车间")


class TeamModelView(AdminModelView):

    __list_columns__ = ["id", "name", "department",
                        column_spec.ColumnSpec("leader_list", formatter=lambda v, obj: ",".join([unicode(i) for i in v]))]

    __create_columns__ = __form_columns__ = ["name",
                                             column_spec.InputColumnSpec("leader_list",
                                                                         filter_=lambda q: q.filter(User.groups.any(Group.id==groups_const.TEAM_LEADER)),
                                                                         doc=u'只有用户组是"班组长"，才能作为班组长'), "department"]

    __column_labels__ = {"id": u"编号", "name": u"名称", "leader_list": u"班组长列表", "department": u"所属车间"}

    __customized_actions__ = [DeleteAction(u"删除", AdminPermission)]

    def populate_obj(self, form):
        return Team(name=form.name.data, department=form.department.data, leader=form.leader_list.data)

team_model_view = TeamModelView(Team, u"班组")

class HarborModelView(AdminModelView):
    __list_columns__ = ["name", "department"]
    __column_labels__ = {"name": u"名称", "department": u"默认车间"}
    __create_columns__ = __form_columns__ = ["name", "department"]
    __customized_actions__ = [DeleteAction(u"删除", AdminPermission)]

harbor_model_view = HarborModelView(Harbor, u"装卸点")


class ProcedureModelView(AdminModelView):
    __column_labels__ = {"name": u"名称", "department_list": u"可以执行此工序的车间"}
    __create_columns__ = __form_columns__ = ["name", "department_list"]
    __customized_actions__ = [DeleteAction(u"删除", AdminPermission)]

procedure_model_view = ProcedureModelView(Procedure, u"工序")

class ConfigModelView(AdminModelView):
    __column_labels__ = {"property_name": u"属性名称", "property_desc": u"描述",
                         "property_value": u"值"}
    def try_create(self):
        raise PermissionDenied

    __form_columns__ = [
        column_spec.InputColumnSpec("property_name", label=u"属性名称",
                                    read_only=True),
        "property_desc",
        "property_value"]

config_model_view = ConfigModelView(Config, u"配置项")

class ProductModelView(AdminModelView):
    """
    产品的管理类
    """
    can_batchly_edit = True
    __list_columns__ = ["id", "MSSQL_ID", "name", "product_type", "enabled"]
    __column_labels__ = {"id": u"产品编号", "MSSQL_ID": u"在mssql的编号",
                         "name": u"名称", "product_type": u"产品类型",
                         "enabled": u"是否启用"}
    __column_formatters__ = {"enabled": lambda v, obj: u"是" if v else u"否"}
    __column_filters__ = [filters.EqualTo("product_type", name=u"是")]
    __batch_form_columns__ = ["product_type", "enabled"]

product_model_view = ProductModelView(Product, u"产品")

@admin2_page.route("/broker/index.html")
@templated("/admin2/broker/index.html")
def broker_index():
    from litefac.portal.admin2 import sub_nav_bar
    return {"nav_bar": nav_bar, "sub_nav_bar": sub_nav_bar}

@admin2_page.route("/broker/products.html")
def import_products():
    import litefac.apis as apis

    types_data = apis.broker.import_types()
    content1 = u"读入%d条产品类型信息，" % len(types_data)
    products_data = apis.broker.import_products()
    content2 = u"读入%d条产品信息，" % sum(len(v) for v in products_data.values())
    content1 += apis.product.post_types(types_data)
    content2 += apis.product.post_product(products_data)
    flash(u"导入成功: " + content1 + "," + content2, 'success')
    return redirect(url_for("admin2.broker_index"))

@admin2_page.route("/broker/customers.html")
def import_customers():
    import litefac.apis as apis

    customers = apis.broker.import_customers()
    content = u"读入%d条客户信息，" % len(customers)
    content += apis.customer.post_customers(customers)
    flash(u"导入成功: " + content, 'success')
    return redirect(url_for("admin2.broker_index"))

@admin2_page.route("/broker/consigments.html")
def export_consignments():
    import litefac.apis as apis

    current_consignments, totalcnt = apis.delivery.get_consignment_list(exporting=True)
    content = u"读出%d条发货单信息，" % len(current_consignments)
    count = 0
    for consignment in current_consignments:
        MSSQL_ID = json.loads(apis.broker.export_consignment(consignment))

        apis.delivery.ConsignmentWrapper.update(consignment.id,
                                                MSSQL_ID=MSSQL_ID["id"])
        count += 1
    content += u"成功导出%d条发货单" % count
    flash(u"导出成功: " + content, 'success')
    return redirect(url_for("admin2.broker_index"))

@admin2_page.route("/broker/team-performance.html", methods=["GET", "POST"])
def team_performance():
    class _DateForm(Form):
        begin_date = DateField("begin_date")
        end_date = DateField("end")
    if request.method == "GET":
        form = _DateForm(request.args)
        begin_date = form.begin_date.data
        end_date = form.end_date.data

        if not begin_date or not end_date:
            #TODO no result yet
            pass
        elif begin_date > end_date:
            begin_date, end_date = end_date, begin_date

        from litefac.portal.admin2 import sub_nav_bar
        return render_template("/admin2/broker/team-performance.html",
                               titlename=u"班组绩效管理", begin_date=begin_date,
                           end_date=end_date, nav_bar=nav_bar, sub_nav_bar=sub_nav_bar)
    else:
        class UnicodeWriter:
            """
            A CSV writer which will write rows to CSV file "f",
            which is encoded in the given encoding.
            """

            def __init__(self, f, dialect=csv.excel, **kwds):
                # Redirect output to a queue
                self.queue = cStringIO.StringIO()
                self.writer = csv.writer(self.queue, dialect=dialect,
                                         **kwds)
                self.stream = f
                self.encoder = codecs.getincrementalencoder("UTF-8")()
                self.stream.write(codecs.BOM_UTF8)

            def writerow(self, row):
                self.writer.writerow([s.encode("utf-8") for s in row])
                # Fetch UTF-8 output from the queue ...
                data = self.queue.getvalue()
                data = data.decode("utf-8")
                # ... and reencode it into the target encoding
                data = self.encoder.encode(data)
                # write to the target stream
                self.stream.write(data)
                # empty queue
                self.queue.truncate()

            def writerows(self, rows):
                for row in rows:
                    self.writerow(row)


        from flask import Response
        import litefac.apis as apis

        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
        return_fileobj = StringIO()
        writer = UnicodeWriter(return_fileobj)
        fieldnames = [u'车间', u'班组', u'生产日期', u'工单号', u'生产重量（KG）', u'扣除重量（KG）']
        writer.writerow(fieldnames)
        form = _DateForm(request.form)
        begin_date = form.begin_date.data
        end_date = form.end_date.data
        if begin_date > end_date:
            begin_date, end_date = end_date, begin_date

        for team in apis.manufacture.get_team_list():
            _dict = team.get_team_work_command_dict(begin_date, end_date)
            for item in _dict.items():
                for wc in item[1]:
                    writer.writerow(
                        [team.department.name, team.name, item[0],
                         str(wc.id), str(wc.processed_weight),
                         str(wc.deduction)])
        response = Response(return_fileobj.getvalue(), mimetype='text/csv')
        response.headers[
        'Content-Disposition'] = 'attachment; filename=export.csv'
        return response

