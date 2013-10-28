# -*- coding: UTF-8 -*-

from flask import Blueprint

report_page = Blueprint("report", __name__, static_folder="static", 
                       template_folder="templates")
