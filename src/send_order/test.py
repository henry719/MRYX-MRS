#!/usr/bin/env python
# -*- coding:utf-8 -*- 
"""
一个python文件
"""
import os
import logging
import logging.handlers
import traceback
import unittest

__author__ = 'dongsibei'

logger = logging.getLogger(__name__)  # 默认日志

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(name)s:%(levelname)s pid:%(process)d thread:%(threadName)s %(pathname)s line:%(lineno)d %(funcName)s:%(message)s",
    # filename=os.path.join(os.getcwd(), 'log.log')
)


def main():
    # 微仓下的商品,使用set去重
    sku_ls = list(set([i.strip().split('\t')[4] for i in itera_ls if len(i.strip().split('\t')) == 5]))
    param = {
        'warehouse': warehouse,  # 微仓编号
        "outerIds": sku_ls  # 微仓下的商品
    }  # 微仓字典参数

    logger.info('I am main')
    pass


# 主函数入口
if __name__ == '__main__':
    logger.debug('this is main.')
    try:
        main()
        xx
    except Exception as e:
        logger.exception('Exception Logged')
        pass
    logger.info('the main end.')


class MyTest(unittest.TestCase):
    # 初始化工作
    def setUp(self):
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
        pass

    # 清理工作
    def tearDown(self):
        pass

    # 语法测试变
    def test_hello(self):
        ls = ['a', 'b']
        try:
            print 'hello'
            print ls[3]
        except Exception as e:
            # info = sys.exc_info()
            # sys.stderr.write(str(info[0]) + ':' + str(info[1]))
            # print info[0],':',info[1]
            traceback.print_exc()
            raise ValueError('参数有错')
            # sys.stderr.write(traceback.format_exc())
            # info = sys.exc_info()
            # print(info)
            # msg = traceback.format_exc()
            # print(msg)
            pass
        pass
