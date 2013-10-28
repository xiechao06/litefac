from flask import Blueprint

manufacture_ws = Blueprint("manufacture_ws", __name__, static_folder="static",
                             template_folder="templates")
from litefac.apis.auth import load_user_from_token
manufacture_ws.before_request(load_user_from_token)

from litefac.portal.manufacture_ws import webservices

