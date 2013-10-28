# -*- coding: utf-8 -*-
import codecs
import csv
import cStringIO
from datetime import datetime
from flask import request
from litefac.portal.op import op_page
import litefac.constants as constants
from litefac.utilities import decorators, _
from litefac.utilities.pagination import Pagination

def _trans_order_type(order_type):
    if order_type == constants.STANDARD_ORDER_TYPE:
        return _(u"计重")
    elif order_type == constants.EXTRA_ORDER_TYPE:
        return _(u"计件")
    else:
        return _(u"未知")

def _discard_report_wrapper(qir):
    return dict(id=qir.id, quantity=qir.quantity, weight=qir.weight,
                work_command_id=qir.work_command_id,
                order=qir.work_command.order,
                customer=qir.work_command.order.customer.name,
                unit=qir.work_command.unit,
                product_name=qir.work_command.sub_order.product.name,
                report_time=qir.report_time,
                reporter=qir.reporter.username,
                department=qir.work_command.department.name,
                team=qir.work_command.team.name)

@op_page.route("/", methods=["GET"])
@decorators.templated("op/operation-manager-list.html")
@decorators.nav_bar_set
def index():
    return dict(titlename=_(u"运营管理"))

@op_page.route("/discard-report-list", methods=["GET"])
@decorators.templated("op/discard-report-list.html")
@decorators.nav_bar_set
def discard_report_list():
    page = request.args.get("page", 1, type=int)
    page_size = constants.ITEMS_PER_PAGE
    import litefac.apis as apis
    qir_list, total_cnt = apis.quality_inspection.get_qir_list(
        idx=(page - 1) * page_size,
        cnt=page_size, finished_only=True,
        result=constants.quality_inspection.DISCARD)
    pagination = Pagination(page, page_size, total_cnt)
    dr_list = [_discard_report_wrapper(qir) for qir in qir_list]
    return dict(titlename=_(u"报废单管理"), dr_list=dr_list, pagination=pagination)


@op_page.route("/team-performance")
@decorators.templated("op/team-performance.html")
@decorators.nav_bar_set
def team_performance():
    import litefac.apis as apis
    page = request.args.get("page", 1, type=int)
    orders, total_cnt = apis.order.get_order_list(
        (page - 1) * constants.ORDER_PER_PAGE, constants.ORDER_PER_PAGE)
    if orders is None:
        orders = []
    pagination = Pagination(page, constants.ORDER_PER_PAGE, total_cnt)

    department_list = apis.manufacture.get_department_list()
    team_list = []
    for dep in department_list:
        team_list.extend(apis.manufacture.get_team_list(dep.id))
    return dict(titlename=_(u"班组绩效管理"), order_list=orders,
                team_list=team_list, pagination=pagination, page=page)


@op_page.route("/export.csv", methods=["POST"])
def export2csv():
    import litefac.apis as apis
    class UnicodeWriter:
        """
        A CSV writer which will write rows to CSV file "f",
        which is encoded in the given encoding.
        """

        def __init__(self, f, dialect=csv.excel, **kwds):
            # Redirect output to a queue
            self.queue = cStringIO.StringIO()
            self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
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

    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    return_fileobj = StringIO()
    writer = UnicodeWriter(return_fileobj)
    fieldnames = [u'班组', u'生产日期',u'工单号' , u'生产重量（KG）', u'扣除重量（KG）']
    writer.writerow(fieldnames)
    begin_date_s = request.form.get("begin_date")
    begin_date, end_date = None, None
    if begin_date_s:
        begin_date =  datetime.strptime(begin_date_s,"%Y-%m-%d")
    end_date_s = request.form.get("end_date")
    if end_date_s:
        end_date =  datetime.strptime(end_date_s,"%Y-%m-%d")
    department_list = apis.manufacture.get_department_list()
    team_list = []
    for dep in department_list:
        team_list.extend(apis.manufacture.get_team_list(dep.id))
    for team in team_list:
        _dict = team.get_team_work_command_dict(begin_date, end_date)
        for item in _dict.items():
            for wc in item[1]:
                writer.writerow([team.name, item[0], str(wc.id), str(wc.processed_weight), str(wc.deduction)])
    response = Response(return_fileobj.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=export.csv'
    return response



