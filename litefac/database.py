# -*- coding: utf-8 -*-
from litefac.basemain import app
app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DBSTR"]
from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

from CodernityDB.database import Database

codernity_db = Database(app.config['CODERNITY_DATABASE_PATH'])
if codernity_db.exists():
    codernity_db.open()
    codernity_db.reindex()
else:
    codernity_db.create()

app.config["MONGODB_DB"] = "localhost"

def init_db():
    # 必须要import models, 否则不会建立表
    from litefac import models
    db.create_all()

