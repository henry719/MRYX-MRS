#!/usr/bin/env python
# -*- coding:utf-8 -*- 
"""
一个python文件
"""
import fire
import MySQLdb
import sys

reload(sys)
sys.setdefaultencoding('utf-8')


# 获取BI数据库连接 bi_bak 补货系统的数据源
def getBiMysqlConn():
    conn = MySQLdb.connect(
        host='10.10.131.156', port=3306,
        user='bi_u28', passwd='ki*safsaHb-d',
        db='bi_bak', charset='utf8'
    )
    return conn


# 查询数据
def getQueryData(sql):
    conn = getBiMysqlConn()
    cur = conn.cursor()
    result = cur.execute(sql)
    info = cur.fetchmany(result)
    for item in info:
        print(
            '\t'.join(
                map(
                    lambda x: x.strip().replace('\t', ''),
                    map(str, item)
                )
            )
        )
    pass


# noinspection SqlDialectInspection
def main():
    print('hello')
    sql = """
        -- 查询x微仓y品
        SELECT
            daqu, -- 大区编号
            daqu1, -- 大区名称
            vc_warehouse, -- 微仓编码
            weicang_hanzi, -- 微仓名称
            vc_material_id, -- 原料id
            `name`, -- 原料名称
            new_pinlei, -- 品类名称
            l_xsck_sl, -- 实际出库量
            lilunxiaoliang, -- 理论销量
            yuxiajia, -- 预下架
            vc_batch -- 日期
        FROM
            bi_bak.shj_yuanliao_xiaoshou_infor_all_month
        WHERE
            vc_batch >= '2018-06-01'
        AND vc_material_id = '1001206'
        AND vc_warehouse = 'MRYXBJN-ANDINGMEN'
    """
    getQueryData(sql)
    pass


if __name__ == '__main__':
    fire.Fire()
    pass
