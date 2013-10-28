#! /usr/bin/env python
# -*- coding: UTF-8 -*-

"""
本脚本用于创建测试数据，是为了帮助进行随意测试。本脚本基于数据库的初始化脚本
"""

from hashlib import md5
from datetime import datetime, date
from litefac.constants import (groups, work_command as wc_const,
                                quality_inspection, cargo as cargo_const,
                                delivery as delivery_const)
import litefac.basemain
import litefac.constants as const
from setuptools import Command
from litefac.models import *
from litefac.utilities import do_commit
from litefac.database import db, init_db


class InitializeTestDB(Command):
    def initialize_options(self):
        """init options"""
        pass

    def finalize_options(self):
        """finalize options"""
        pass

    def run(self):
        from litefac.tools import build_db
        db.drop_all()
        init_db()
        build_db.build_db()

        # 创建产品类型以及产品
        product_type1 = do_commit(ProductType(name=u"A"))
        product_type2 = do_commit(ProductType(name=u"B"))
        product1 = do_commit(Product(name=u'A01', product_type=product_type1))
        product2 = do_commit(Product(name=u'A02', product_type=product_type1))
        product3 = do_commit(Product(name=u'A03', product_type=product_type1))
        product4 = do_commit(Product(name=u'B01', product_type=product_type2))

        # 创建用户
        cargo_clerk = Group.query.get(groups.CARGO_CLERK)
        department_leader = Group.query.get(groups.DEPARTMENT_LEADER)
        team_leader = Group.query.get(groups.TEAM_LEADER)
        quality_inspector = Group.query.get(groups.QUALITY_INSPECTOR)
        loader = Group.query.get(groups.LOADER)
        # 收发员
        cc = do_commit(User(username='cc', password=md5('cc').hexdigest(),
                            groups=[cargo_clerk]))
        # 车间1主任
        d1_dl = do_commit(
            User(username='d1', password=md5('d1').hexdigest(),
                 groups=[department_leader]))
        # 车间2主任
        d2_dl = do_commit(
            User(username='d2', password=md5('d2').hexdigest(),
                 groups=[department_leader]))
        # 超级车间主任
        super_dl = do_commit(
            User(username='super_dl', password=md5('super_dl').hexdigest(),
                 groups=[department_leader]))
        # 班组101班组长
        t101_tl = do_commit(
            User(username='t101', password=md5('t101').hexdigest(),
                 groups=[team_leader]))
        # 质检员
        qi = do_commit(
            User(username='qi', password=md5('qi').hexdigest(),
                 groups=[quality_inspector]))
        # 装卸工
        l = do_commit(User(username='l', password=md5('l').hexdigest(),
                           groups=[loader]))

        # 创建车间和班组
        department1 = do_commit(Department(name=u"车间1",
                                           leader_list=[d1_dl, super_dl]))
        department2 = do_commit(Department(name=u"车间2",
                                           leader_list=[d2_dl, super_dl]))
        team1 = do_commit(Team(name=u"班组101", department=department1,
                               leader_list=[t101_tl]))

        # 创建工序
        procedure1 = do_commit(Procedure(name=u"工序1",
                                         department_list=[department1,
                                                          department2]))
        procedure2 = do_commit(Procedure(name=u"工序2",
                                         department_list=[department2]))

        # 初始化装卸点
        harbor1 = do_commit(Harbor(name=u"装卸点1", department=department1))
        harbor2 = do_commit(Harbor(name=u"装卸点2", department=department2))

        # 初始化车辆
        vehicle1 = do_commit(Plate(name=u"浙A 00001"))
        vehicle2 = do_commit(Plate(name=u"浙A 00002"))
        vehicle3 = do_commit(Plate(name=u"浙A 00003"))

        # 初始化客户
        customer1 = do_commit(Customer(u"宁波机床场", "nbjcc"))
        customer2 = do_commit(Customer(u"宁力紧固件", "nljgj"))
        customer3 = do_commit(Customer(u"宁波造船场", "nbzcc"))

        # 收货环节
        #     - 车上有人, 有两个任务, 分别来自不同的客户, 并且都已经称重
        unload_session1 = do_commit(
            UnloadSession(plate_=vehicle1,
                          gross_weight=10000,
                          with_person=True,
                          finish_time=datetime.now(),
                          status=cargo_const.STATUS_CLOSED))
        default_product = Product.query.filter(
            Product.name == const.DEFAULT_PRODUCT_NAME).one()
        do_commit(UnloadTask(unload_session=unload_session1,
                             harbor=harbor1,
                             customer=customer1, creator=l,
                             product=default_product,
                             pic_path="0.png",
                             weight=1000))
        do_commit(UnloadTask(unload_session=unload_session1,
                             harbor=harbor2,
                             customer=customer2,
                             creator=l, product=product2,
                             pic_path="1.jpg",
                             weight=3000))
        #     - 车上无人， 有三个任务，来自两个客户, 有一个尚未称重
        unload_session2 = do_commit(
            UnloadSession(plate_=vehicle2, gross_weight=10000,
                          with_person=False,
                          status=cargo_const.STATUS_WEIGHING))
        do_commit(UnloadTask(unload_session=unload_session2, harbor=harbor1,
                             customer=customer2, creator=l, product=product2,
                             pic_path="2.png",
                             weight=1000))
        do_commit(UnloadTask(unload_session=unload_session2,
                             harbor=harbor2, customer=customer3, creator=l,
                             product=product3, pic_path="3.png",
                             weight=4000))
        do_commit(UnloadTask(unload_session=unload_session2, harbor=harbor2,
                             customer=customer3, creator=l,
                             product=product4,
                             pic_path="4.png"))
        #     - 车上无人，正在等待装货
        do_commit(UnloadSession(plate_=vehicle3, gross_weight=10000,
                                with_person=False,
                                status=cargo_const.STATUS_LOADING))

        # 生成收货会话和收货项, 注意这里故意不为某些客户生成收货单
        goods_receipt1 = do_commit(
            GoodsReceipt(customer1, unload_session1))
        do_commit(GoodsReceiptEntry(goods_receipt=goods_receipt1, weight=1000,
                                    product=product1, harbor=harbor1))
        do_commit(GoodsReceiptEntry(goods_receipt=goods_receipt1, weight=3000,
                                    product=product2, harbor=harbor2))
        goods_receipt2 = do_commit(
            GoodsReceipt(customer2, unload_session1))
        # 生成订单, 注意这里故意不为某些收货会话生成订单
        #     - 生成一个已经下发的订单
        order1 = do_commit(
            Order(goods_receipt1, creator=cc, dispatched=True, refined=True))
        #     - 生成一个尚未下发的订单
        do_commit(Order(goods_receipt2, creator=cc))
        # 生成子订单，注意这里故意不为某些订单生成子订单
        #     - 生成计重类型的子订单, 还有50公斤没有分配出去
        sub_order1 = do_commit(
            SubOrder(product1, 300, harbor1, order1, 300, "KG",
                     due_time=date.today(), default_harbor=harbor1,
                     returned=True))
        do_commit(SubOrder(product2, 1000, harbor2, order1, 1000, "KG",
                           due_time=date.today(), default_harbor=harbor2,
                           returned=True))
        #     - 生成计件类型的子订单，
        sub_order2 = do_commit(
            SubOrder(product=product3, weight=3000,
                     harbor=harbor2,
                     order=order1, quantity=10,
                     unit=u'桶',
                     order_type=const.EXTRA_ORDER_TYPE,
                     due_time=date.today(), default_harbor=harbor2))

        # 生成工单
        #     - DISPATCHING STATUS
        do_commit(WorkCommand(sub_order=sub_order1,
                              org_weight=50,
                              procedure=procedure1,
                              tech_req=u"工单1的技术要求",
                              urgent=False, org_cnt=50,
                              pic_path="1.jpg"))
        do_commit(WorkCommand(sub_order=sub_order2,
                              org_weight=300,
                              procedure=procedure0,
                              tech_req=u'foo tech requirements',
                              org_cnt=1))

        #     - ASSIGNING STATUS
        do_commit(WorkCommand(sub_order=sub_order1,
                              org_weight=50,
                              procedure=procedure1,
                              tech_req=u"工单2的技术要求",
                              urgent=False, org_cnt=50,
                              department=department1,
                              status=wc_const.STATUS_ASSIGNING,
                              pic_path="1.jpg"))
        do_commit(WorkCommand(sub_order=sub_order2,
                              org_weight=300,
                              procedure=procedure1,
                              tech_req=u"foo tech requirements",
                              urgent=False,
                              org_cnt=1,
                              department=department1,
                              status=wc_const.STATUS_ASSIGNING,
                              pic_path="1.jpg"))
        #     - ENDING STATUS
        do_commit(WorkCommand(sub_order=sub_order1,
                              org_weight=50,
                              procedure=procedure2,
                              tech_req=u"工单3的技术要求",
                              urgent=False, org_cnt=100,
                              pic_path="1.jpg",
                              status=wc_const.STATUS_ENDING,
                              department=department1,
                              team=team1))
        do_commit(WorkCommand(sub_order=sub_order2,
                              org_weight=300,
                              procedure=procedure2,
                              tech_req=u"foo tech requirements",
                              urgent=False,
                              org_cnt=1,
                              pic_path="1.jpg",
                              status=wc_const.STATUS_ENDING,
                              department=department1,
                              team=team1))
        #     - QUALITY INSPECTING STATUS
        work_command4 = WorkCommand(sub_order=sub_order1,
                                    org_weight=50,
                                    procedure=procedure2,
                                    tech_req=u"工单4的技术要求",
                                    urgent=False, org_cnt=50,
                                    pic_path="1.jpg",
                                    status=wc_const.STATUS_QUALITY_INSPECTING,
                                    department=department1,
                                    team=team1,
                                    processed_weight=50)
        work_command5 = WorkCommand(sub_order=sub_order2,
                                    org_weight=300,
                                    procedure=procedure2,
                                    tech_req=u"foo tech requirements",
                                    urgent=False,
                                    org_cnt=1,
                                    pic_path="1.jpg",
                                    status=wc_const.STATUS_QUALITY_INSPECTING,
                                    department=department1,
                                    team=team1,
                                    processed_weight=300,
                                    processed_cnt=1)
        do_commit([work_command4, work_command5])

        #     - FINISHED STATUS
        work_command6 = WorkCommand(sub_order=sub_order1,
                                    org_weight=50,
                                    processed_weight=50,
                                    procedure=procedure2,
                                    tech_req=u"foo tech requirements",
                                    urgent=False, org_cnt=50,
                                    processed_cnt=50,
                                    pic_path="1.jpg",
                                    status=wc_const.STATUS_FINISHED,
                                    department=department1,
                                    team=team1)
        work_command6.completed_time = datetime.now()
        work_command7 = WorkCommand(sub_order=sub_order2,
                                    org_weight=600,
                                    org_cnt=2,
                                    processed_weight=600,
                                    processed_cnt=2,
                                    procedure=procedure2,
                                    tech_req=u"foo tech requirements",
                                    urgent=False,
                                    pic_path="1.jpg",
                                    status=wc_const.STATUS_FINISHED,
                                    department=department1,
                                    team=team1)
        work_command7.completed_time = datetime.now()
        do_commit([work_command6, work_command7])

        qir1 = do_commit(QIReport(work_command6, 20, 20,
                                  quality_inspection.FINISHED, qi.id,
                                  pic_path='1.jpg'))
        do_commit(QIReport(work_command6, 10, 10,
                           quality_inspection.NEXT_PROCEDURE, qi.id,
                           pic_path='1.jpg'))
        do_commit(QIReport(work_command6, 10, 10,
                           quality_inspection.REPAIR, qi.id,
                           pic_path='1.jpg'))
        do_commit(QIReport(work_command6, 10, 10,
                           quality_inspection.REPLATE, qi.id,
                           pic_path='1.jpg'))

        qir3 = do_commit(QIReport(work_command7, 1, 300,
                                  quality_inspection.FINISHED, qi.id,
                                  pic_path='1.jpg'))
        do_commit(QIReport(work_command7, 1, 300,
                           quality_inspection.REPLATE, qi.id,
                           pic_path='1.jpg'))

        delivery_session = DeliverySession(plate=vehicle1.name,
                                           tare=2300,
                                           status=delivery_const.STATUS_CLOSED)
        do_commit(delivery_session)
        delivery_task = do_commit(DeliveryTask(delivery_session, cc.id))
        store_bill1 = StoreBill(qir1)
        store_bill1.delivery_task = delivery_task
        store_bill2 = StoreBill(qir3)
        store_bill2.delivery_task = delivery_task
        do_commit([store_bill1, store_bill2])

        consignment = Consignment(customer1, delivery_session, True)
        consignment.actor = cc
        consignment.notes = "".join(str(i) for i in xrange(100))
        consignment.MSSQL_ID = 1
        do_commit(consignment)
        cp = ConsignmentProduct(product1, delivery_task, consignment)
        cp.unit = u"桶"
        cp.weight = 100
        cp.returned_weight = 50
        do_commit(cp)

if __name__ == "__main__":
    from distutils.dist import Distribution
    InitializeTestDB(Distribution()).run()
