# -*- coding: UTF-8 -*-
import json


def login(username, password, app):
    rv = app.post('/auth/login', data=dict(username=username,
                                           password=password))
    assert rv.status_code == 302


def client_login(username, password, app):
    rv = app.post('/auth_ws/login?username=%s&password=%s' %
                  (username, password))
    assert rv.status_code == 200
    return json.loads(rv.data)['token']
