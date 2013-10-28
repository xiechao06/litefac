# -*- coding: utf-8 -*-
import tempfile
import os
from lettuce import *

@before.each_feature
def setup(feature):
    from litefac.basemain import app
    from litefac.database import db, init_db
    db_fd, db_fname = tempfile.mkstemp()
    os.close(db_fd)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_fname
    try:
        db.init_app(app)
    except AssertionError:  # 这是因为flask禁止在一次请求之后再次init_app, 而
                            # 使用lettuce, 这是不可避免的
        pass 
    init_db()
    world.db = db
    world.db_fname = db_fname

@after.each_feature
def teardown(feature):
    os.unlink(world.db_fname)
