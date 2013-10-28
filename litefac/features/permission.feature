# -*- coding: utf-8 -*-
Feature: 测试基于need的permission机制
    Scenario: 将某个权限赋予用户后，该用户就拥有了该权限 
        Given 创建如下权限:
            | name  |
            | 飞翔  |
            |  奔跑 |
        And 创建用户组"鸟类", 关联如下权限:
            | name  |
            |  飞翔 |
            |  奔跑 |
        And 创建用户组"哺乳类", 关联如下权限:
            | name  |
            | 奔跑  |
        And 创建如下用户:
            | username  | password  | group    |
            | 唐老鸭    | tly       | 鸟类     |
            | 米奇老鼠  | mqls      | 哺乳类   |
        And 在系统中安装如下权限:
            | permission | need |
            | 飞翔       | fly  |
            | 奔跑       | run  |
        Then 用户(唐老鸭:tly)登陆后, 可以:
            | permission |
            | 飞翔       |
            | 奔跑       |
        Then 用户(米奇老鼠:mqls)登陆后, 可以:
            | permission |
            | 奔跑       |
        Then 用户(米奇老鼠:mqls)登陆后, 不可以:
            | permission |
            | 飞翔       |

