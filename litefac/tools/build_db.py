# -*- coding: utf-8 -*-
"""
SYNOPSIS
    python build_db.py [options]
BRIEF
    本脚本用来初始化lite-mms, 包括预设的权限，用户组，帐号，权限，产品类型，产品等等,
    TODO: 目前这个脚本的初始化, 完全是基于金禾域的组织架构
OPTIONS
    -h
        show this help
    -s  <dbstr>
        the db connection string
"""
from hashlib import md5
import sys
from getopt import getopt
from flask import url_for
from litefac.basemain import app
import litefac.constants.groups as groups
import litefac.constants as constants
from litefac.permissions import permissions
from litefac.utilities import do_commit

def build_db():
    msg = u"初始化开始, 数据库是: " + app.config["SQLALCHEMY_DATABASE_URI"]
    app.logger.info(msg)
    import os
    dbstr = app.config["SQLALCHEMY_DATABASE_URI"]
    if dbstr.startswith("sqlite"):
        dir = os.path.split(dbstr[10:])[0]
        if dir and not os.path.exists(dir):
            os.makedirs(dir)
    from litefac.database import db, init_db
    from litefac import models
    db.drop_all()
    init_db()
    session = db.session

    # 初始化权限
    for k, v in permissions.items():
        do_commit(models.Permission(name=k, desc=v["brief"]))

    with app.test_request_context():
        app.preprocess_request()
        # 初始化用户组，目前内置的用户组包括, 这些用户组本来就带有基于角色的权限
        #   - 收发员
        cargo_clerk = models.Group(id=groups.CARGO_CLERK, name=u"收发员", default_url=url_for("cargo.index"))
        cargo_clerk.permissions = models.Permission.query.filter(
            models.Permission.name.like("%view_order%")).all()
        cargo_clerk = do_commit(cargo_clerk)
        #   - 调度员
        scheduler = models.Group(id=groups.SCHEDULER, name=u"调度员", default_url=url_for("order.index"))
        scheduler.permissions = models.Permission.query.filter(
            models.Permission.name.like(
                "%schedule_order%")).all() + models.Permission.query.filter(
            models.Permission.name.like("work_command%")).all()
        scheduler = do_commit(scheduler)
        #   - 车间主任
        department_leader = models.Group(id=groups.DEPARTMENT_LEADER, name=u"车间主任", default_url=url_for("manufacture.work_command_list"))
        department_leader = do_commit(department_leader)
        #   - 班组长
        team_leader = do_commit(models.Group(id=groups.TEAM_LEADER, name=u"班组长"))
        #   - 质检员
        quality_inspector = models.Group(id=groups.QUALITY_INSPECTOR, name=u"质检员", default_url=url_for("store_bill.index"))
        quality_inspector.permissions = models.Permission.query.filter(
            models.Permission.name.like("%view_work_command")).all()
        quality_inspector = do_commit(quality_inspector)
        #   - 装卸工
        loader = do_commit(models.Group(id=groups.LOADER, name=u"装卸工"))
        #   - 财会人员
        accountant = models.Group(id=groups.ACCOUNTANT, name=u"财会人员", default_url=url_for("consignment.consignment_list"))
        accountant.permissions = [models.Permission.query.filter(models.Permission.name.like("%export_consignment%")).one()]
        accountant = do_commit(accountant)
        #   - 管理员
        administrator = models.Group(id=groups.ADMINISTRATOR, name=u"管理员", default_url=url_for("admin2.index"))
        administrator.permissions = models.Permission.query.all()
        administrator = do_commit(administrator)

        # 初始化超级用户
        admin = models.User(username='admin', password=md5('admin').hexdigest(), groups=[administrator])
        admin.id = constants.ADMIN_USER_ID
        admin = do_commit(admin)

        # 设置默认产品类型和产品
        product_type_default = do_commit(models.ProductType(constants.DEFAULT_PRODUCT_TYPE_NAME))
        do_commit(models.Product(constants.DEFAULT_PRODUCT_NAME, product_type_default))
        session.flush()

        msg = u"初始化完成"
        app.logger.info(msg)

if __name__ == "__main__":
    opts, _ = getopt(sys.argv[1:], "s:h")
    for o, v in opts:
        if o == "-h":
            print __doc__
            exit(1)
        else:
            print "unknown option: " + o
    build_db()
