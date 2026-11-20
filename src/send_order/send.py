#!/usr/bin/env python
# -*- coding:utf-8 -*- 
"""
一个python文件
"""

import os
import sys
import json
import logging
import logging.handlers
import traceback
import unittest
import urllib2
from itertools import groupby
import threadpool
import redis

import time
from datetime import datetime

reload(sys)
# noinspection PyUnresolvedReferences
sys.setdefaultencoding('utf8')

__author__ = 'dongsibei'

logger = logging.getLogger(__name__)  # 默认日志
logger.setLevel(logging.DEBUG)

# 日志格式
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s:%(levelname)s pid:%(process)d thread:%(threadName)s %(pathname)s line:%(lineno)d %(funcName)s: %(message)s"
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

# 连接redis 用于创建自增id
r = redis.Redis(host='127.0.0.1', port=6379, db=0, password='admin')


def getSerial():
    """
    获取唯一id
    :return: result
    """
    result = None
    sn = r.get('serial')
    if sn is None:
        result = r.incr('serial', 1)
        r.expire('serial', 3600 * 24 * 2)
    else:
        result = r.incr('serial')
    return result


def getLockData(data):
    """
    构造锁库存对象
    :param data: 单据对象
    :return: lock_stock_data
    """
    date = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    # 锁库存对象
    lock_stock_data = {
        "fromERP": "algo",
        "warehouse": data.get('warehouse'),
        "order_type": "BH",
        "area_type": 1,
        "t_id": data.get('t_id'),
        "send_time": date
    }

    mid_ls = []  # 组织原料数据
    for item in data.get('data'):
        mid = item.get('materialsId')  # 原料
        quantity = item.get('quantity')
        mid_ls.append({
            "quantity": quantity,
            "internal_id": mid,
            "material_id": mid,
            "material_num": quantity
        })
    lock_stock_data['materials'] = mid_ls
    return lock_stock_data


def postReturnStock(lock_stock_data):
    """
    归还库存
    :param lock_stock_data: 锁库存对象
    :return: 状态码,消息
    """
    code = -1
    msg = ""
    """
    try:
        url = 'http://172.16.30.79:18001/atp/cancelOrder_DT.json'  # 归还库存
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
            "Content-Type": "application/json"
        }
        request = urllib2.Request(url=url, data=json.dumps(lock_stock_data), headers=header)
        response = urllib2.urlopen(request)
        code = response.code
        msg = response.read()
    except Exception as e:
        logger.exception(e)
    # """
    code = 201
    msg = 'success'
    return code, msg


def postLockData(lock_data):
    """
    发送锁库存请求
    :param lock_data: 锁库存对象
    :return:
    """
    code = -1  # 状态码
    msg = ""  # 消息
    """
    try:
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
            "Content-Type": "application/json"
        }
        url = 'http://172.16.30.79:18001/atp/createOrder_DT.json'  # 锁库存url
        request = urllib2.Request(url=url, data=json.dumps(lock_data), headers=header)  # 创建请求
        response = urllib2.urlopen(request)
        code = response.code
        msg = response.read()
    except Exception as e:
        logger.exception(e)
    # """
    code = 201
    msg = 'success'
    return code, msg


def postPsm(data):
    """
    发送的补货订单数据
    :param data: 补货单数据
    :return: 状态标识,消息
    """
    flag = False
    msg = ""

    try:
        url = ' http://172.16.30.79:18002/psm-service/PSM/send_save_buhuodan.json'  # 测试环境地址
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
            "Content-Type": "application/json"
        }
        request = urllib2.Request(url=url, data=json.dumps(data), headers=header)
        response = urllib2.urlopen(request)
        code = response.code
        result = json.loads(response.read())
        flag = result.get('success')
        msg = result.get('msg')
    except Exception as e:
        logger.exception(e)

    return flag, msg


def sendOrderData(order_data):
    """
    发送一条补货单
    :param order_data:补货单数据
    :return:
    """
    lock_data = getLockData(order_data)  # 构造锁库存对象
    code, msg = postLockData(lock_data)  # 锁库存

    send_id = order_data["t_id"]  # 单号
    vc = order_data["warehouse"]  # 微仓编码
    data_str = json.dumps(order_data)  # 数据字符串

    if code == 201:
        # 锁库存成功
        flag, msg = postPsm(order_data)  # 执行推单
        if flag:
            # 推单成功
            logger.info(
                "补货单发送成功,单号:%s,微仓:%s,data:%s",
                send_id, vc, data_str
            )
        else:
            # 推单失败
            logger.error(
                "补货单发送失败,单号:%s,微仓:%s,msg:%s,data:%s",
                send_id, vc, msg, data_str
            )

            # 回滚库存
            code, msg = postReturnStock(lock_data)
            if code == 201:
                # 回滚成功
                logger.info(
                    "补货单还库存成功,单号:%s,微仓:%s,data:%s",
                    send_id, vc, data_str
                )
            else:
                # 回滚失败
                logger.error(
                    "补货单还库存失败,code:%s,msg:%s,单号:%s,微仓:%s,data:%s",
                    code, msg, send_id, vc, data_str
                )
    else:
        # 锁库存失败
        logger.error(
            "补货单锁库存失败,code:%s,msg:%s,单号:%s,data:%s",
            code, msg, send_id, data_str
        )
        pass


def send():
    """
    推送补货单
    :return:
    """
    start = time.time()

    today = datetime.today().strftime('%Y%m%d')
    hms = datetime.now().strftime('%H%M%S')

    data_ls = []  # 请求列表
    j = 0
    for vc, group in groupby(open('data/1/wh_material_yb.txt'), key=lambda x: x.split('\t')[0]):
        # 调试微仓数量
        j += 1
        if j > 300:
            break

        # 构造补货单
        mid_list = []
        mid = None

        i = 0
        for line in group:
            # 调试原料数量
            i += 1
            if i > 200:
                break

            # 微仓编码 原料id 应补数量 日期
            vc, mid, yb, dp = line.strip().split('\t')
            item = {"materialsId": mid, "quantity": float(yb)}
            mid_list.append(item)
            pass
        # @todo 用于测试
        if vc == 'MRYXBJN-WANGJING':
            vc = 'MRYXTJ-WANGJING'
        # vc = 'MRYXTJ-WANGJING'  # 用于测试成功的情况
        # logger.info('微仓:%s,原料:%s,原料数量:%s', vc, mid, len(mid_list))
        sn = getSerial()  # 获取唯一序列id
        send_id = '{vc}_{today}_{hms}_{sn}'.format(vc=vc, today=today, hms=hms, sn=sn)  # 单据编号
        order_data = {"t_id": send_id, "warehouse": vc, "bch": "14", "bch2": "other", "data": mid_list}
        data_ls.append(order_data)

    # """ 发起多线程
    poll = threadpool.ThreadPool(1)  # 线程池
    requests = threadpool.makeRequests(sendOrderData, data_ls)  # 创造多线程请求
    [poll.putRequest(req) for req in requests]
    poll.wait()
    # """

    logger.info('end 总耗时:%s秒', time.time() - start)
    pass


# 主函数入口
if __name__ == '__main__':
    logger.info('start send order')
    try:
        send()  # 发送补货单
    except Exception as e:
        logger.exception('Exception Logged')
    logger.info('end send order')


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

    def test_request(self):
        param = {
            "t_id": "5465w4e65w4er65we",  # 唯一补货单号
            "warehouse": "MRYXBJN-RITAN",  # 要补货的微仓
            "bch": "14",  # 波次号
            "bch2": "其它",  # 波次号2
            "data": [  # 原料id-数量
                {
                    "materialsId": "6005914",  # 原料id
                    "quantity": 2  # 应补数量
                },
                {
                    "materialsId": "6005768",
                    "quantity": 1
                },
                {
                    "materialsId": "6005914",
                    "quantity": 1
                }
            ]
        }
        result = requestPsm(json.dumps(param))  # 发送请求
        print result

    def test_redis(self):
        r = redis.Redis(host='127.0.0.1', port=6379, db=0, password='admin')
        r.set('foo', 'Bar')
        print(r.get('foo'))

        # 创建自增id
        a = r.incr('serial', 1)
        r.expire('serial', 3600 * 24 * 2)  # 过期时间两天
        print a
        a = r.incr('serial', 5)
        print a
        a = r.incr('serial')
        print a
        a = int(r.get('serial'))
        print a
