from flask import Blueprint

auth_ws = Blueprint("auth_ws", __name__, static_folder="static", 
    template_folder="templates")

import litefac.portal.auth_ws.webservices





