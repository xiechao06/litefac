# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
import codecs
import csv
import cStringIO
import errno
from flask import url_for, abort, request, render_template, json
from flask.ext.admin import expose, BaseView
from litefac.utilities import _
from jinja2 import Markup
from wtforms import Form, DateField
from litefac.permissions import AdminPermission

class DataAdminView(BaseView):

    def create_blueprint(self, admin):
        if not self.blueprint:
            blueprint = super(DataAdminView, self).create_blueprint(admin)
            # 必须在这里注册，因为只有在注册blueprint时，blueprint的errorhandler
            # 才能够加入app。而flask-admin是在add_view时，注册blueprint
            import socket

            @blueprint.errorhandler(socket.error)
            def connection_refused(e):
                if e.errno == errno.ECONNREFUSED:
                    dic = dict(error_content=u"无法连接", titlename=u"无法连接")
                    return self.render("admin/result.html", **dic)

            self.blueprint = blueprint
        return self.blueprint

    def is_accessible(self):
        return AdminPermission.can()

    @expose("/")
    def index(self):
        return self.render("/import_data/index.html")


    @expose("/products")
    def products(self):
        import litefac.apis as apis

        types_data = apis.broker.import_types()
        content1 = u"读入%d条产品类型信息，" % len(types_data)
        products_data = apis.broker.import_products()
        content2 = u"读入%d条产品信息，" % sum(len(v) for v in products_data.values())
        content1 += apis.product.post_types(types_data)
        content2 += apis.product.post_product(products_data)
        return self.render("admin/result.html", titlename=u"导入成功",
                           content=Markup(content1 + r"<br/>" + content2),
                           back_url=url_for(".index"))


    @expose("/customers")
    def customers(self):
        import litefac.apis as apis

        customers = apis.broker.import_customers()
        content = u"读入%d条客户信息，" % len(customers)
        content += apis.customer.post_customers(customers)
        return self.render("admin/result.html", titlename=u"导入成功",
                           content=content,
                           back_url=url_for(".index"))

    @expose("/consignments")
    def consignments(self):
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
        return self.render("admin/result.html", titlename=u"导出成功",
                           content=content,
                           back_url=url_for('.index'))

    @expose("/team-performance", methods=["GET", "POST"])
    def team_performance(self):
        class _DateForm(Form):
            begin_date = DateField("begin_date")
            end_date = DateField("end")


        if request.method == "GET":
            form = _DateForm(request.args)
            begin_date = form.begin_date.data
            end_date = form.end_date.data

            if not begin_date or not end_date:
                #TODO
                pass
            elif begin_date > end_date:
                begin_date, end_date = end_date, begin_date

            return self.render("admin/team-performance.html",
                               titlename=_(u"班组绩效管理"), begin_date=begin_date,
                               end_date=end_date)
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

