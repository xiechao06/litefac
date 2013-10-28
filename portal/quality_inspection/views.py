#-*- coding:utf-8 -*-
from flask.ext.databrowser import ModelView, column_spec
from flask.ext.principal import PermissionDenied
from litefac import models
from litefac.permissions.roles import QualityInspectorPermission


class QIR(ModelView):
    edit_template = "quality_inspection/qireport.html"

    def try_create(self):
        raise PermissionDenied

    def try_edit(self, processed_objs=None):
        QualityInspectorPermission.test()
        if processed_objs and any(obj.store_bill_list for obj in processed_objs):
            raise PermissionDenied

    def edit_hint_message(self, obj, read_only=False):
        if read_only:
            if QualityInspectorPermission.can():
                return u"已生成仓单的质检报告%s不能修改" % obj.id
            else:
                return u"您没有修改质检报告%s的权限" % obj.id
        else:
            return super(QIR, self).edit_hint_message(obj, read_only)

    __column_labels__ = {"id": u"编号", "quantity": u"数量", "weight": u"重量", }

    from litefac.apis.quality_inspection import get_QI_result_list

    __form_columns__ = [column_spec.ColumnSpec("id"), "weight", "quantity",
                        column_spec.ColumnSpec('unit', label=u"单位"),
                        column_spec.SelectColumnSpec(col_name="result", label=u"质检结果", choices=get_QI_result_list()),
                        column_spec.ColumnSpec("work_command", label=u"工单编号"),
                        column_spec.ColumnSpec("report_time", label=u"创建时间"),
                        column_spec.ColumnSpec("actor", label=u"质检员"),
                        column_spec.PlaceHolderColumnSpec("pic_url", template_fname="pic-snippet.html", label=u"图片")]

    def preprocess(self, obj):
        from litefac.apis.quality_inspection import QIReportWrapper
        return QIReportWrapper(obj)



qir_model_view = QIR(model=models.QIReport)