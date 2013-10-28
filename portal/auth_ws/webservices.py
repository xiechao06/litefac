# -*- coding: UTF-8 -*-
from litefac.portal.auth_ws import auth_ws
from litefac.utilities.decorators import webservice_call
from litefac.exceptions import AuthenticateFailure
from flask import abort, request
import json
from litefac.utilities import _
from litefac.constants import groups

@auth_ws.route("/login", methods=["POST"])
@webservice_call("json")
def login():
    username = request.args.get("username", type=str)
    password = request.args.get("password", type=str)
    if not username or not password:
        return _(u"需要username或者password字段"), 403
    try:
        import litefac.apis as apis

        user = apis.auth.authenticate(username, password)
        if not user.can_login_client:
            return json.dumps({
                'reason': u'该用户不能在客户端登录'
            }), 403
    except AuthenticateFailure as inst:
        return json.dumps({
            'reason': unicode(inst)
        }), 403
    return json.dumps(
        dict(username=user.username,
             teamID=",".join([str(team.id) for team in user.team_list]) if user.team_list else "",
             userID=user.id, departmentID=",".join([str(department.id) for department in
                                                    user.department_list]) if user.department_list else "",
             userGroup=user.groups[0].id, token=user.get_auth_token()))

if __name__ == "__main__":
    try:
        # pylint: disable=F0401,W0611
        from litefac.instance.portal.auth import webservices_main
        # pylint: enable=F0401,W0611
    except ImportError:
        import traceback

        print "can't import webservice_main.py"
        traceback.print_exc()
