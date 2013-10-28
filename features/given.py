# -*- coding: utf-8 -*-
from lettuce import step, world
from hashlib import md5
from collections import namedtuple

@step(u'创建如下权限:')
def create_permissions(step):
    from litefac import models
    for perm_dict in step.hashes:
        perm = models.Permission(name=perm_dict["name"])
        world.db.session.add(perm)
    world.db.session.commit()

@step(u'创建用户组"(.*)", 关联如下权限:')
def create_group_with_permissions(step, group_name):
    from litefac import models
    group = models.Group(group_name)
    import random
    group.id = random.randint(99999, 199999)
    for perm_dict in step.hashes:
        perm = models.Permission.query.filter(models.Permission.name==perm_dict["name"]).one()
        group.permissions.append(perm)
    world.db.session.add(group)
    world.db.session.commit()

@step(u'创建如下用户:')
def create_user(step):
    from litefac import models
    for user_dict in step.hashes:
        group = models.Group.query.filter(models.Group.name==user_dict["group"]).one()
        user = models.User(user_dict["username"], md5(user_dict["password"]).hexdigest(), [group])
        world.db.session.add(user)
    world.db.session.commit()

@step(u'在系统中安装如下权限:')
def install_permissions(step):
    from litefac.permissions import install_permission, reset_permissions
    for perm_dict in step.hashes:
        install_permission(perm_dict["permission"], [namedtuple(perm_dict["need"], [])], "")

@step(u"生成如下用户组:")
def create_groups(step):
    from litefac import models
    for group_dict in step.hashes:
        group = models.Group(group_dict["group_name"], group_dict["default_url"])
        world.db.session.add(group)
    world.db.session.commit()

@step(u"创建如下view:")
def create_views(step):
    from flask import url_for
    from litefac.basemain import app
    for view_dict in step.hashes:
        exec('def %s(): return "%s"' % (view_dict["name"], view_dict["content"]))
        app.route(view_dict["url"])(locals()[view_dict["name"]])
