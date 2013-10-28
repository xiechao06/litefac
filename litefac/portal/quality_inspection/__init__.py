#-*- coding:utf-8 -*-
from flask import Blueprint

from litefac.basemain import data_browser, nav_bar

from litefac.portal.quality_inspection.views import qir_model_view

qir_page = Blueprint("qir", __name__, static_folder="static", template_folder="templates")
data_browser.register_model_view(qir_model_view, qir_page, {"form_view": {"nav_bar": nav_bar, "titlename": u"质检报告"}})