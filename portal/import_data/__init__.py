# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
from flask import Blueprint

import_data_page = Blueprint("import_data", __name__, static_folder="static",
                             template_folder="templates")

from . import views
