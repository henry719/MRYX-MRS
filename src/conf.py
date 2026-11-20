#!/usr/bin/env python
# -*- coding:utf-8 -*- 
"""
一个python文件
"""

__author__ = 'dongsibei'

day_span = 28  # 日期跨度 天数
run_day = '20180515'  # 运算的日期

flag = 'test'  # 生产环境:prod  测试环境:test 开发环境:dev

if flag == 'prod':
    hive_database = 'dw'  # 数据输出hive数据库 线上默认值:dw
    yy_database = 'da'  # 预测的应有库存保存位置, 线上默认值:da
elif flag == 'test':
    hive_database = 'supply'  # 数据输出hive数据库 , 测试库默认值:supply
    yy_database = 'supply'  # 预测的应有库存保存位置, 测试库默认值:supply
elif flag == 'dev':
    hive_database = 'dd'  # 数据输出hive数据库 , 开发默认值:dd
    yy_database = 'dd'  # 预测的应有库存保存位置, 开发默认值:dd


# 主函数入口
if __name__ == '__main__':
    pass
