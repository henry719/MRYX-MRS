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

logger = logging.getLogger("send")  # 默认日志
logger.setLevel(logging.DEBUG)

# logging.basicConfig(
#     level=logging.DEBUG,
#     format="[%(asctime)s] %(name)s:%(levelname)s pid:%(process)d thread:%(threadName)s %(pathname)s line:%(lineno)d %(funcName)s:%(message)s",
#     filename=os.path.join(os.getcwd(), 'log.log')
# )

# 日志格式
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s:%(levelname)s pid:%(process)d thread:%(threadName)s %(pathname)s line:%(lineno)d %(funcName)s:%(message)s"
)

info_file = logging.FileHandler(os.path.join(os.getcwd(), 'log.log'))
# 滚动日志
# filehandler = logging.handlers.RotatingFileHandler(os.path.join(os.getcwd(), 'log.log'), maxBytes=20,backupCount=5)
# filehandler = logging.handlers.TimedRotatingFileHandler(os.path.join(os.getcwd(), 'log.log'), when='D',backupCount=3)
info_file.setFormatter(formatter)
info_file.setLevel(logging.DEBUG)

# 创建过滤器 不输出ERROR
# info_filter = logging.Filter()
# info_filter.filter = lambda recoder: recoder.levelno not in {logging.ERROR}
# info_file.addFilter(info_filter)

# 错误日志
error_file = logging.FileHandler(os.path.join(os.getcwd(), 'err.log'))
error_file.setLevel(logging.ERROR)
error_file.setFormatter(formatter)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))

# 添加 logHandler
logger.addHandler(info_file)  # 消息打印
logger.addHandler(error_file)  # 错误打印
# logger.addHandler(console)  # 控制台打印


def main():
    logger.info('I am main')
    pass


# 主函数入口
if __name__ == '__main__':
    logger.debug('this is main start')
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
