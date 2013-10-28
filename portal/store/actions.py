#-*- coding:utf-8 -*-
from flask.ext.databrowser.action import DirectAction
from flask import redirect, url_for, request


class PreviewPrintAction(DirectAction):
    def op_upon_list(self, objs, model_view):
        if len(objs):
            return redirect(url_for("store_bill.store_bill_preview", id_=objs[0].id, url=request.url))

    def test_enabled(self, model):
        if not model.harbor:
            return -2
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"该仓单%s没有存放点，请先修改"}