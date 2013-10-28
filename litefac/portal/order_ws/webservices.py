from litefac.portal.order_ws import order_ws
from litefac.utilities.decorators import webservice_call, login_required_webservice
import json

@order_ws.route("/customer-list")
@webservice_call("json")
@login_required_webservice
def customer_list():
    import litefac.apis as apis
    customers = apis.customer.get_customer_list()
    return json.dumps([{"id": c.id, "name": c.name, "abbr": c.abbr} for c in customers if c.enabled])
