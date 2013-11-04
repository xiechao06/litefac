# -*- coding: utf-8 -*-
"""
用户类
"""
from hashlib import md5

from flask import session, g, _request_ctx_stack, current_app, request
import flask.ext.login as login
from flask.ext.principal import identity_changed, Identity, AnonymousIdentity
from sqlalchemy.orm.exc import NoResultFound
from litefac.exceptions import AuthenticateFailure
from litefac.apis import ModelWrapper
from litefac.basemain import app
from itsdangerous import URLSafeTimedSerializer, BadTimeSignature
from litefac.constants import groups

class UserWrapper(login.UserMixin, ModelWrapper):
    """
    a wrapper of the actual user model
    """
    __serializer__ = URLSafeTimedSerializer(secret_key=app.config.get('SECRET_KEY'), salt=app.config.get('SECURITY_SALT'))

    @property
    def default_url(self):
        return self.group.default_url

    @property
    def permissions(self):
        ret = set()
        for perm in self.group.permissions:
            ret.add(perm)
        return ret

    @property
    def group(self):
        for group in self.groups:
            if group.id == int(session['current_group_id']):
                return group
        return self.groups[0]

    @property
    def group_name(self):
        """
        get the group name of the **FIRST** group that user belongs
        """
        return self.group.name

    def __eq__(self, other):
        """
        比较。如果id相同，则认为相同
        :param other: 比较的对象
        :return:True or False
        """
        return isinstance(other, UserWrapper) and self.id == other.id

    def __repr__(self):
        return "<UserWrapper %s> " % self.username

    @property
    def can_login_client(self):
        """
        test if the user could login in client
        """
        can_login_groups = {
            groups.DEPARTMENT_LEADER,
            groups.TEAM_LEADER,
            groups.LOADER,
            groups.QUALITY_INSPECTOR
        }
        return all(group.id in can_login_groups for group in self.groups)


    def get_auth_token(self):
        '''
        get the authentiaction token, see `https://flask-login.readthedocs.org/en/latest/#flask.ext.login.LoginManager.token_loader`_
        '''
        return self.__serializer__.dumps([self.id, self.username, self.password])

def get_user(id_):
    if not id_:
        return None
        # TODO 这里需要优化
    from litefac import models

    try:
        return UserWrapper(
            models.User.query.filter(models.User.id == id_).one())
    except NoResultFound:
        return None

def load_user_from_token():
    ctx = _request_ctx_stack.top
    token = request.args.get('auth_token')
    user_id = None
    identity = AnonymousIdentity()
    if token is None:
        ctx.user = current_app.login_manager.anonymous_user()
    else:
        try:
            ctx.user = get_user(UserWrapper.__serializer__.loads(token)[0])
            identity = Identity(ctx.user.id)
            # change identity to reset permissions
        except BadTimeSignature:
            ctx.user = current_app.login_manager.anonymous_user()
    identity_changed.send(current_app._get_current_object(), identity=identity)

def get_user_list(group_id=None):
    from litefac import models
    q = models.User.query
    if group_id:
        q = q.filter(models.User.groups.any(models.Group.id == group_id))
    return [UserWrapper(user) for user in q.all()]

def authenticate(username, password):
    """
    authenticate a user, test if username and password mathing
    :return: an authenticated User or None if can't authenticated
    :rtype: User
    :raise: exceptions.AuthenticateFailure
    """
    try:
        from litefac import models

        return UserWrapper(
            models.User.query.filter(models.User.username == username).filter(
                models.User.password == md5(password).hexdigest()).one())
    except NoResultFound:
        raise AuthenticateFailure("用户名或者密码错误")


if __name__ == "__main__":
    pass
