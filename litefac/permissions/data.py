# -*- coding: UTF-8 -*-
from collections import namedtuple
from flask.ext.principal import Permission

DataManagement = namedtuple("data", ["method"])
ExportConsignment = DataManagement("export_consignment")

export_consignment = Permission(ExportConsignment)
export_consignment.brief = u"导出发货单的权限"

