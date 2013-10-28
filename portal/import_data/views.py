# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
from flask import abort, url_for, json
from socket import error
from litefac.portal.import_data import import_data_page
from litefac.utilities import decorators

@import_data_page.route("/")
@decorators.templated("/data/index.html")
@decorators.nav_bar_set
def index():
    return dict(titlename=u"导入数据管理")


@import_data_page.route("/consignments")
@decorators.templated("result.html")
@decorators.nav_bar_set
def consignments():
    from litefac.permissions.data import export_consignment

    decorators.permission_required(export_consignment, ("POST",))
    from litefac import apis

    try:
        current_consignments,totalcnt = apis.delivery.get_consignment_list(exporting=True)
        content = u"读出%d条发货单信息，" % len(current_consignments)
        count = 0
        for consignment in current_consignments:
            try:
                MSSQL_ID = json.loads(
                    apis.broker.export_consignment(consignment))
            except error:
                content=u"链接超时"
                return dict(titlename=u"导出失败，链接超时", content=content,
                            back_url=url_for('.index'))

            apis.delivery.ConsignmentWrapper.update(consignment.id,
                                                    MSSQL_ID=MSSQL_ID["id"])
            count += 1
        content += u"成功导出%d条发货单" % count

        return dict(titlename=u"导出成功", content=content,
                    back_url=url_for('.index'))
    except ValueError, e:
        abort(500, e)


