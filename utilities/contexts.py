# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
from contextlib import contextmanager
from litefac.basemain import app


@contextmanager
def keep_db_session_alive():
    """
    该上下文用于确保db session在request context弹出的时候，不会被删除（而flask-sqlalchemy会自动将db session删除）
    """
    import mock

    patcher = mock.patch.dict(app.__dict__, {
        "teardown_appcontext_funcs": [f for f in app.teardown_appcontext_funcs if f.__module__ != "flask_sqlalchemy"]})
    patcher.start()
    yield
    patcher.stop()

