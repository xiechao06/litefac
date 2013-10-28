# -*- coding: UTF-8 -*-

from flask import Blueprint, render_template, request

work_flow_page = Blueprint("work_flow", __name__, static_folder="static",
                            template_folder="templates")

from litefac.portal.work_flow.views import node_model_view
from litefac.basemain import data_browser, nav_bar

extra_params = {
    "list_view": {
        "nav_bar": nav_bar,
        "titlename": u"工作流任务列表",
    },
    "form_view": {
        "nav_bar": nav_bar,
        "titlename": u"处理工作流任务",
    }

}

data_browser.register_model_view(node_model_view, 
                                 work_flow_page, extra_params)
