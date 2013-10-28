# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
from flask import Blueprint

search_page = Blueprint("search", __name__, static_folder="static",
                        template_folder="templates")

from . import views