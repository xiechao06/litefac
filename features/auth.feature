# -*- coding: utf-8 -*-
Feature: 测试登陆功能

    Scenario: 当用户登陆后，能够跳转到指定的url
        Given 生成如下用户组:
            | group_name | default_url   |
            | 浙江       | /hangzhou     |
            | 江苏       | /nanjing      |
        And 创建如下view:
            | name      | url       | content       |
            | nanjing   | /nanjing  | 中国江苏南京  |
            | hangzhou  | /hangzhou | 中国浙江杭州  |
        And 创建如下用户:
            | username | password | group   |
            | 鲁迅     | lx       | 浙江    |
            | 华罗庚   | hlg      | 江苏    |
        Then 用户(鲁迅:lx)登陆后, 获取的内容是"中国浙江杭州"
        Then 用户(华罗庚:hlg)登陆后, 获取的内容是"中国江苏南京"
