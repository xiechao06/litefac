from flask import Blueprint

cargo_ws = Blueprint("cargo_ws", __name__, static_folder="static", 
    template_folder="templates")

from litefac.apis.auth import load_user_from_token
cargo_ws.before_request(load_user_from_token)

from litefac.portal.cargo_ws import webservices
