# -*- coding: utf-8 -*-

STATUS_DISPATCHING = 1 #: 待排产
STATUS_ASSIGNING = 2 #: 待分配
STATUS_LOCKED = 3 #: 锁定， 待车间主任确认回收
STATUS_ENDING = 4 #: 待结转或结束
STATUS_QUALITY_INSPECTING = 7 #: 待质检
STATUS_REFUSED = 8 #: 车间主任打回
STATUS_FINISHED = 9 #: 已经结束

ACT_CHECK = 201 #: (调度员)检货
ACT_DISPATCH = 202 #: (调度员)排产
ACT_ASSIGN = 203 #: (车间主任)分配工单
ACT_ADD_WEIGHT = 204 #: (班组长)增加工单白件重量
ACT_END = 205 #: (班组长)请求结束 
ACT_CARRY_FORWARD = 206 #: (班组长)请求结转
ACT_REFUSE = 209 #: (车间主任)打回工单
ACT_RETRIEVAL = 210 #: (调度员)请求回收工单
ACT_AFFIRM_RETRIEVAL = 211 #: (车间主任)确认回收
ACT_QI = 212 #: (质检员)质检
ACT_REFUSE_RETRIEVAL = 213 #: (车间主任)拒绝回收
ACT_RETRIVE_QI = 214 #:(质检员)取消质检报告
ACT_QUICK_CARRY_FORWARD = 215 #:(班组长)快速结转

# handle types
HT_NORMAL = 1 #:正常加工
HT_REPLATE = 2 #:返镀
HT_REPAIRE = 3 #:返修

PROCEDURE_FIRST = 1#：第一道工序
PROCEDURE_END = 2#：合格，结束
PROCEDURE_NEXT = 3#：质检完毕转下道工序

CAUSE_NORMAL = 1  # 预排产
CAUSE_NEXT = 2  # 转下道工序
CAUSE_REPAIR = 3  # 返修
CAUSE_REPLATE = 4  # 返镀
CAUSE_CARRY = 5  # 结转