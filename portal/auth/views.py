# -*- coding: UTF-8 -*-
from flask import (request, render_template, redirect, url_for, current_app,
    session, session)
from flask.ext.principal import (Principal, Identity, AnonymousIdentity,
     identity_changed)
from flask.ext.login import current_user
from litefac.portal.auth import auth
from flask.ext.principal import identity_changed, Identity, AnonymousIdentity
from litefac.utilities import _
from litefac.utilities.decorators import after_this_request
from wtforms import PasswordField, TextField, Form, HiddenField
from flask.ext.login import login_user, logout_user, login_required, \
    current_user
from litefac.exceptions import AuthenticateFailure


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user.is_anonymous():
            return render_template("auth/login.html", titlename=u'登录')
        return redirect("/")
    else:
        class LoginForm(Form):
            username = TextField()
            password = PasswordField()
            next_url = HiddenField()

        form = LoginForm(request.form)
        if form.validate():
            username = form.username.data
            password = form.password.data
            try:
                import litefac.apis as apis

                user = apis.auth.authenticate(username, password)
            except AuthenticateFailure:
                return render_template("auth/login.html", error=_(u"用户名或者密码错误"), titlename=u"请登录"), 403
            if not user.enabled:
                return render_template("auth/login.html", error=_(u"该账户已禁用, 请使用其它账户"), titlename=u"请登录"), 403
            if not login_user(user):
                return render_template("auth/login.html", error=_(u"登陆失败"), titlename=u"请登录"), 403

            identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))
            return redirect(form.next_url.data or "/")
        else:
            return render_template("auth/login.html", error=_(u"请输入用户名及密码"), titlename=u"请登录"), 403

@auth.route("/logout")
@login_required
def logout():
    try:
        logout_user()
    except Exception: # in case sesson expire
        pass
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())

    next_url = request.args.get("next", "/")
    return redirect(next_url)

@auth.route("/switch-group/<int:id_>")
def switch_group(id_):
    # let it happen at once
    session['current_group_id'] = id_
    @after_this_request
    def set_group_id(response):
        response.set_cookie('current_group_id', str(id_))
        return response
    return redirect("/")

