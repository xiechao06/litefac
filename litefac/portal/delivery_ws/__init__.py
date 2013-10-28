from flask import Blueprint

delivery_ws = Blueprint("delivery_ws", __name__, static_folder="static",
                        template_folder="templates")

from litefac.apis.auth import load_user_from_token
delivery_ws.before_request(load_user_from_token)

from litefac.portal.delivery_ws import webservices

