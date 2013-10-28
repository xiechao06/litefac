# -*- coding: utf-8 -*-
from hashlib import md5
from collections import namedtuple
from lettuce import step, world
from nose.tools import assert_equals
from flask import url_for

@step(u'用户\((.*):(.*)\)登陆后, 可以:')
def after_login_then_could(step, username, password):
    from litefac.basemain import app
    from litefac.permissions import permissions
    import flask.ext.principal as principal
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post(url_for("auth.login"), data=dict(username=username, password=password)) 
            assert rv.status_code == 302
            from flask.ext.login import current_user
            for perm_dict in step.hashes:
                need = permissions[perm_dict["permission"]]["needs"][0]
                perm = principal.Permission(need)
                assert perm.can()

@step(u'用户\((.*):(.*)\)登陆后, 不可以:')
def after_login_then_could(step, username, password):
    from litefac.basemain import app
    from litefac.permissions import permissions
    import flask.ext.principal as principal
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post(url_for("auth.login"), data=dict(username=username, password=password)) 
            assert rv.status_code == 302
            from flask.ext.login import current_user
            for perm_dict in step.hashes:
                need = permissions[perm_dict["permission"]]["needs"][0]
                perm = principal.Permission(need)
                assert not perm.can()

@step(u'用户\((.*):(.*)\)登陆后, 获取的内容是"(.*)"')
def after_login_then_redirect_to(step, username, password, content):
    from litefac.basemain import app
    from litefac.permissions import permissions
    import flask.ext.principal as principal
    with app.test_request_context():
        with app.test_client() as c:
            rv = c.post(url_for("auth.login"), 
                        data=dict(username=username, password=password), 
                        follow_redirects=True) 
            assert_equals(rv.status_code, 200)
            assert_equals(rv.data.decode("utf-8"), content)
