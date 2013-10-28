from flask import Blueprint

order_ws = Blueprint("order_ws", __name__, static_folder="static",
    template_folder="templates")

from litefac.apis.auth import load_user_from_token
order_ws.before_request(load_user_from_token)

from litefac.portal.order_ws import webservices

