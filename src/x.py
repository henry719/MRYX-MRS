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

filehandler = logging.FileHandler(os.path.join(os.getcwd(), 'log.log'))
# 滚动日志
# filehandler = logging.handlers.RotatingFileHandler(os.path.join(os.getcwd(), 'log.log'), maxBytes=20,backupCount=5)
# filehandler = logging.handlers.TimedRotatingFileHandler(os.path.join(os.getcwd(), 'log.log'), when='D',backupCount=3)

# 日志格式
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s:%(levelname)s pid:%(process)d thread:%(threadName)s %(pathname)s line:%(lineno)d %(funcName)s:%(message)s")
filehandler.setFormatter(formatter)

# 定义一个Handler打印DEBUG及以上级别的日志到sys.stderr
# 设置日志打印格式
# 将定义好的console日志handler添加到root logger
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# formatter = logging.Formatter("[%(asctime)s] %(name)s:%(levelname)s: %(message)s")
# console.setFormatter(formatter)

# 创建名字为log的日志对象
logger = logging.getLogger()  # 没有名字的时候默认返回rootlogger
logger.addHandler(filehandler)  # 添加文件打印
logger.addHandler(console)  # 添加控制台打印


def main():
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

    def test_filter(self):
        data = "1.2#20180515##1.5#20180516##1.3#20180517##2.8#20180518##3.4#20180519##2.0#20180520##2.1#20180521"
        mts = data.split('##')
        mts = list(filter(
            lambda x: x.split('#')[-1] not in {'20180517', '20180518', '20180519', '20180520'}, mts)
        )
        print mts
        pass
