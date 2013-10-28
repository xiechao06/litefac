# -*- coding: UTF-8 -*-
from flask import (redirect, send_from_directory, url_for, abort, render_template, request, json, g)
from flask.ext.login import current_user, login_required
from flask.helpers import safe_join
from litefac.basemain import app, nav_bar
from litefac.utilities import decorators


@app.route("/")
def index():
    if current_user.is_authenticated():
        next_url = current_user.default_url
    else:
        next_url = url_for("auth.login")
    if not next_url:
        return render_template("index.html", nav_bar=nav_bar, titlename=u"首页")
    return redirect(next_url)


@app.route("/error")
def error():
    return render_template("error.html", msg=request.args["msg"], back_url=request.args.get("back_url", "/"),
                           nav_bar=nav_bar, titlename=u"错误")


@app.route("/index")
@decorators.templated("index.html")
@login_required
@decorators.nav_bar_set
def default():
    return dict(titelname=u"首页")


@app.route("/serv-pic/<filename>")
def serv_pic(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def _resize_file(filename, size=(180, 180)):
    _dir = app.config['UPLOAD_FOLDER']
    new_filename = filename.replace(".", "-%d%d." % size)
    import os

    if not os.path.exists(safe_join(_dir, new_filename)):
        from PIL import Image

        try:
            im = Image.open(safe_join(_dir, filename))
            ori_w, ori_h = im.size
            if ori_w > ori_h:
                _size = size[0], ori_h * size[1] / ori_w
            else:
                _size = ori_w * size[0] / ori_h, size[1]
            im.resize(_size, Image.ANTIALIAS).save(safe_join(_dir, new_filename), "JPEG")
        except IOError:
            pass
    return new_filename

@app.route("/serv-small-pic/<filename>")
def serv_small_pic(filename):
    new_filename = _resize_file(filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], new_filename)


@app.route("/message")
def ajax_new_message():
    from litefac.models import TODO
    from litefac.apis.todo import get_all_notify

    messages = [
        {
            "create_time": str(todo.create_time),
            "actor": todo.actor.username if todo.actor else "",
            "action": todo.action,
            "msg": todo.msg,
            "context_url": todo.context_url
        }
        for todo in get_all_notify(current_user.id)
    ]
    return json.dumps({"total_cnt": TODO.query.filter(TODO.user_id == current_user.id).count(), "messages": messages})

