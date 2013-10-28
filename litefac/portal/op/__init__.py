from flask import Blueprint

op_page = Blueprint("op_page", __name__, static_folder="static", 
    template_folder="templates")

import litefac.portal.op.views


