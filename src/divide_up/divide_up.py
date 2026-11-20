#!/usr/bin/env python
# -*- coding:utf-8 -*- 
"""
分配策略
"""
import os
import logging
import logging.handlers
import traceback
import unittest

import fire

__author__ = 'dongsibei'

logger = logging.getLogger(__name__)  # 默认日志

format = "[%(asctime)s] %(name)s:%(levelname)s pid:%(process)d thread:%(threadName)s %(pathname)s line:%(lineno)d %(funcName)s:%(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] (levelname)s line:%(lineno)d %(funcName)s:%(message)s",
    # filename=os.path.join(os.getcwd(), 'log.log')
)


def getGcd(x, y):
    """
    Greatest Common Divisor 公约数
    返回最大公约数
    :param x:
    :param y:
    :return:
    """
    r = 1
    while r != 0:
        r = x % y
        x, y = y, r
    return x


def main():
    # """
    # data = [(10, 0), (30, 0), (60, 0)]
    data = [(10, 5), (30, 20), (60, 25)]
    data.sort(key=lambda x: x[0], reverse=True)  # 倒序排列
    total = 21  # 大仓库存

    gcd = reduce(getGcd, [i for i, j in data])  # 应有库存最大公约数
    logger.info('最大公约数:%s' % gcd)

    sum_facotr = sum([i / gcd for i, j in data])
    logger.info('因子之和:%s' % sum_facotr)

    logger.info('微仓应有：%s' % [i for i, j in data])

    ratio_ls = [float(i) / gcd / sum_facotr for i, j in data]  # 各微仓应有库存比例
    logger.info('微仓应有比例:%s' % ratio_ls)

    sum_inv = sum([j for i, j in data]) + total  # 微仓库存与大仓库存之和
    remainder = sum_inv % sum_facotr  # 余数
    logger.info('余数:%s', remainder)

    th_total = sum_inv - remainder
    thr_allocation_ls = [i * th_total for i in ratio_ls]  # 理论分配列表
    logger.info('理论分配列表:%s' % thr_allocation_ls)
    logger.info('微仓库存列表:%s' % [j for i, j in data])

    should_assign_ls = [a - b for a, b in zip(thr_allocation_ls, [j for i, j in data])]  # 应补数量
    logger.info('应补数量列表:%s' % should_assign_ls)

    # 余数分配
    remainder_assign_ls = [round(i * remainder) for i in ratio_ls]
    logger.info('余数分配:%s' % remainder_assign_ls)

    should_assign_ls = [a + b for a, b in zip(should_assign_ls, remainder_assign_ls)]
    logger.info('应补数量之和:%s, 大仓库存:%s' % (sum(should_assign_ls), total))

    last_inv_ls = [a + b for a, b in zip(should_assign_ls, [j for i, j in data])]  # 分配后库存
    logger.info("最后库存:%s" % last_inv_ls)
    last_ratio_ls = ['%s:%s=%s' % (a, b, a / b) for a, b in zip(last_inv_ls, [i for i, j in data])]
    logger.info("最后比例:%s" % last_ratio_ls)

    # """
    # maxFactor(6, 9)
    pass


# 主函数入口
if __name__ == '__main__':
    main()
    # fire.Fire()
    pass


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

    def test_hehe(self):
        # print maxFactor(16, 6)
        # print GYS(16, 6)
        print gcdIter(16, 6)
        print gcdIter(6, 16)
        pass
