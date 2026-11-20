#!/usr/bin/env python
# -*- coding:utf-8 -*- 
"""
一个python文件
"""
import json
import logging
import logging.handlers
import os
import random
import traceback
import sys
import urllib2
from itertools import groupby
from datetime import datetime, timedelta

import MySQLdb
import fire

from rule_map import getValueFromMapRuleCore, RuleMapDto

reload(sys)
# noinspection PyUnresolvedReferences
sys.setdefaultencoding('utf-8')

__author__ = 'dongsibei'

logger = logging.getLogger(__name__)  # 默认日志

# """
formater = "[%(asctime)s] %(name)s:%(levelname)s pid:%(process)d thread:%(threadName)s %(pathname)s line:%(lineno)d %(funcName)s:%(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] line:%(lineno)d :%(message)s",
    # filename=os.path.join(os.getcwd(), 'log.log')
)


# """


def getBiMysqlConn():
    conn = MySQLdb.connect(
        host='10.10.75.56', port=3306,
        user='bi_user', passwd='congku_#2018',
        db='dws', charset='utf8'
    )
    return conn


def getMysqlConn():
    conn = MySQLdb.connect(
        host='10.10.120.27', port=3306,
        user='data_use_r', passwd='jWQVAYD_EO-wTu6-',
        db='psm', charset="utf8"
    )
    return conn


# 查询sql
def getQueryData(sql, conn_name='psm'):
    conn = None
    if conn_name == 'bi':
        conn = getBiMysqlConn()
    else:
        conn = getMysqlConn()

    cur = conn.cursor()
    try:
        result = cur.execute(sql)
        info = cur.fetchmany(result)
        for items in info:
            print('\t'.join(map(lambda x: x.strip().replace('\t', ''), map(str, items))))
    except Exception as e:
        traceback.print_exc()
    finally:
        cur.close()
    pass


# 明天是否营业, 过年那几天是不营业的
# noinspection SqlDialectInspection
def loadStopShopData():
    sql = """
          SELECT
            blg, -- 日期
            `value` -- 说明
          FROM psm_holidays_config where `value` LIKE '%休';
        """
    getQueryData(sql)
    pass


# 获取大仓列表
# noinspection SqlDialectInspection
def loadWhData():
    sql = """
            SELECT
              t.id, -- 大仓编码
              t.name, -- 大仓名称
              t.warehouse_live, -- 生存周期
              t.city -- 城市名称
            FROM master_warehouse t
            WHERE type = 'ZC' AND delete_flag = FALSE;
        """
    getQueryData(sql)
    pass


# 大仓原料的七平均天销量
# noinspection SqlDialectInspection
def loadMidSale7Day():
    sql = """
        SELECT
          t.wh, -- 大仓编码
          t.mid, -- 原料id
          avg(t.total) AS avg_sale -- 平均销量
        FROM
          (
            SELECT
              substring_index(o.warehouse_code, '-', 1) AS wh, -- 大仓编码
              m.materials_id                            AS mid, -- 原料id
              SUM(od.num)                               AS total, -- 总销量
              date_format(o.pay_time, '%Y-%m-%d')       AS pay_day -- 日期
            FROM
              oms_order o LEFT JOIN oms_order_detail od ON o.order_id = od.order_id
              LEFT JOIN master_sku s ON od.goods_no = s.sku_id
              LEFT JOIN master_bom b ON s.sku_id = b.sku_id
              LEFT JOIN master_materials m ON b.materials_id = m.materials_id
            WHERE o.`status` <> 40
                  AND o.pay_time >= date_sub(curdate(), INTERVAL 6 DAY)
                  AND o.pay_time < date_add(curdate(), INTERVAL 1 DAY)
                  AND o.warehouse_code LIKE '%-%'
                  AND o.order_type = 10
                  AND m.category NOT IN ('包材', '礼品')
            GROUP BY wh, mid, pay_day
            ORDER BY wh, mid, pay_day
          ) AS t
        GROUP BY wh, mid
        ORDER BY avg_sale DESC;
          """
    getQueryData(sql)
    pass


# 原料级别
def doMidLevel(total):
    """
    原料级别划分
    :param total:
    :return:
    """
    level_A = total * 0.8
    level_B = total * 0.95

    sum_sale = 0.0
    for line in open('data/1/midsale_7day.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 原料id 销量
        wh, mid, sale = cols
        sum_sale += float(sale)

        level = ''
        if sum_sale < level_A:
            level = 'A'
        elif sum_sale < level_B:
            level = 'B'
        else:
            level = 'C'
        print('\t'.join([wh, mid, level]))


# 15天内首次售卖日期
# noinspection SqlDialectInspection
def loadFirstSaleDay():
    sql = """
        SELECT
          substring_index(t.warehouse, '-', 1) AS daqu, -- 大仓编码
          t.material_id, -- 原料id
          DATEDIFF(now(),MIN(t.batch))                         AS days -- 批次日期
        FROM
          psm_sales_data t
        WHERE t.create_date > date_sub(curdate(), INTERVAL 15 DAY)
              AND t.warehouse LIKE '%-%'
        GROUP BY substring_index(t.warehouse, '-', 1), t.material_id;
    """
    getQueryData(sql)
    pass


# 今日已补
# noinspection SqlDialectInspection
def loadAlreadySupply():
    sql = """
        SELECT
          t.warehouse, -- 微仓编码
          k.material, -- 原料id
          SUM(k.quantity) AS quantity
        FROM
          psm_purchase t,
          psm_purchase_detail k
        WHERE
          t.purchase_id = k.purchase_id
          AND t.type = 'BH'
          AND t.bch2 <> '干仓'
          AND t.`status` <> 40
          AND t.`status` <> 4
          AND t.`status` <> 30
          AND t.batch = curdate()
        GROUP BY t.warehouse, k.material;
    """
    getQueryData(sql)
    pass


# 辅料
# noinspection SqlDialectInspection
def loadSubMid():
    sql = """
        SELECT
          a.sku_id, -- 商品sku
          a.materials_id -- 原料id
        FROM master_bom a LEFT JOIN psm_buhuo_m2m_skus b ON a.sku_id = b.sku AND a.materials_id = b.material
        WHERE b.material IS NULL;
    """
    getQueryData(sql)
    pass


# 微仓订单数量,两天内(昨天今天)
# noinspection SqlDialectInspection
def loadVcOrder():
    sql = """
        SELECT
          t.warehouse_code AS warehouse, -- 微仓编码
          count(1)         AS qty -- 订单量
        FROM
          oms_order t
        WHERE
          t.pay_time >= date_sub(curdate(), INTERVAL 1 DAY)
          AND t.pay_time < date_add(curdate(), INTERVAL 1 DAY)
          AND t.order_type = 10
          AND t.`status` <> 40
          AND t.warehouse_code IS NOT NULL
        GROUP BY t.warehouse_code;
    """
    getQueryData(sql)


# 微仓品类订单量,一周内
# noinspection SqlDialectInspection
def loadVcCateOrder():
    sql = """
        SELECT
          t.warehouse_code, -- 微仓编码
          t.category, -- 品类
          ROUND(avg(t.qty), 0) AS qty -- 平均单量
        FROM psm_riqi_cangku_pinlei_xiaoliang t
        WHERE t.batch > date_sub(curdate(), INTERVAL 8 DAY) AND t.batch < curdate()
        GROUP BY t.category, t.warehouse_code;
    """
    getQueryData(sql)


# 微仓30天四周 品类周平均
# noinspection SqlDialectInspection
def loadVcCate30DayWeekMean():
    sql = """
        SELECT
          tb.warehouse_code,
          tb.category,
          avg(tb.avg_qty) AS avg -- 4周平均
        FROM (
               -- 按周数取平均
               SELECT
                 t.warehouse_code, -- 微仓编码
                 t.category, -- 品类
                 avg(t.qty) AS avg_qty, -- 周平均销量
                 t.weeks -- 一年中的第几周
               FROM (
                      -- 获取30天的数据
                      SELECT
                        warehouse_code, -- 微仓编码
                        category, -- 品类
                        qty, -- 数量
                        DATE_FORMAT(batch, '%Y_%u') AS weeks -- 周
                      FROM psm_riqi_cangku_pinlei_xiaoliang
                      WHERE batch <= subdate(curdate(), date_format(curdate(), '%w'))
                            AND batch >=subdate(subdate(curdate(), date_format(curdate(), '%w')),30)
                            AND warehouse_code LIKE '%-%'
                      ORDER BY warehouse_code,category,weeks DESC
                    ) AS t
               GROUP BY t.warehouse_code,t.category,t.weeks
               ORDER BY t.warehouse_code,t.category,t.weeks,avg_qty ASC
             ) AS tb
        GROUP BY tb.warehouse_code, tb.category, tb.weeks
    """
    getQueryData(sql)
    pass


# 计算微仓品类明日占比(新明日占比)
def doVcCateTomrrowRatio():
    # 周X平均
    week_avg = {}  # 微仓,品类 -> 平均值
    for line in open('data/1/vc_cate_weekavg.txt'):
        cols = line.strip().split('\t')
        vc, cate, value = cols
        key = ','.join([vc, cate])
        if value != 'None':
            v = round(float(value), 5)
        else:
            v = 0.0
        week_avg[key] = v

    for line in open('data/1/vc_cate_30day_weekavg.txt'):
        cols = line.strip().split('\t')
        vc, cate, value = cols
        key = ','.join([vc, cate])

        if value != 'None':
            week30day_avg = round(float(value), 5)
        else:
            week30day_avg = 0.0

        ratio = 1.0
        if key in week_avg and week_avg[key] > 0 and week30day_avg != 0:
            ratio = round(week_avg[key] / week30day_avg, 5)

        ls = [vc, cate, ratio]
        print('\t'.join(map(str, ls)))
    pass


# 微仓7日平均单量
# noinspection SqlDialectInspection
def loadVcOrder_7DayAvg():
    sql = """
        SELECT
          b.warehouse, -- 微仓编号
          avg(b.total) AS avg_sale -- 订单量
        FROM
          (
            SELECT
              t.warehouse_code                    AS warehouse, -- 微仓编码
              count(1)                       AS total, -- 订单量
              date_format(t.pay_time, '%Y-%m-%d') AS pay_day -- 日期
            FROM
              oms_order t
            WHERE t.order_type = 10
                  AND t.`status` <> 40
                  AND t.pay_time >= date_sub(curdate(), INTERVAL 6 DAY)
                  AND t.pay_time < date_add(curdate(), INTERVAL 1 DAY)
                  AND t.warehouse_code like '%-%'
            GROUP BY t.warehouse_code, pay_day
          ) AS b
        GROUP BY b.warehouse
        ORDER BY avg_sale DESC;
    """
    getQueryData(sql)
    pass


# 默认站点等级
default_vc_level = {
    "MRYXBJN-TONGZHOUBEI": "A",
    "MRYXBJN-SHILIUZHUANG": "B",
    "MRYXBJN-MAJIAPU": "B",
    "MRYXBJN-PUHUANGYU": "B",
    "MRYXBJN-YANGQIAO": "B",
    "MRYXBJN-ZHONGGUANCUN": "B",
    "MRYXBJN-NANSHATAN": "B",
    "MRYXBJN-BAOFUSI": "B",
    "MRYXBJN-WUDAOKOU": "B",
    "MRYXBJN-QINGHUA": "B",
    "MRYXBJN-RENDA": "B",
    "MRYXBJN-JIAODA": "B",
    "MRYXBJN-WEIGONGCUN": "B",
    "MRYXBJN-BEISHATAN": "B",
    "MRYXBJN-MADIAN": "B",
    "MRYXBJN-JIUGONG": "B",
    "MRYXBJN-CAIHUYING": "B",
    "MRYXBJN-JIANGTAI": "B",
    "MRYXBJN-MAJIALOU": "B",
    "MRYXBJN-BAJIAOQIAO": "B",
    "MRYXBJN-GAOBEIDIAN": "B",
    "MRYXTJ-XINGANG": "B",
    "MRYXBJN-XIHONGMEN": "B",
    "MRYXTJ-SHUNYI": "B",
    "MRYXTJ-HOUSHAYU": "B",
    "MRYXBJN-FENGTAIKEJIYUAN": "B",
    "MRYXBJN-SHUANGQIAO": "B",
    "MRYXBJN-JIANGUOMEN": "B",
    "MRYXBJN-DONGCHENG": "B"
}


# 微仓站点等级
def doVcLevel(total):
    level_A = total * 0.9
    sum_value = 0.0
    for line in open('data/1/vc_order_7dayavg.txt'):
        cols = line.strip().split('\t')
        vc, sale = cols
        sum_value += float(sale)

        level = ''
        if sum_value < level_A:
            level = 'A'
        else:
            level = 'B'

        print('\t'.join([vc, level]))
    pass


# 新品、促销品
# noinspection SqlDialectInspection
def loadNewsAndPromo():
    sql = """
        SELECT
          t.daqu, -- 大区
          t.city, -- 城市名称
          t.material, -- 原料id
          t.is_main, -- 是否主料
          t.rebate,
          t.total_qty
        FROM psm_active_configure t
        WHERE STR_TO_DATE(t.batch,'%Y-%m-%d') = DATE_ADD(curdate(),INTERVAL 1 DAY);
    """
    getQueryData(sql)
    pass


# 获取新品促销品
def getNewsAndPromo(wh, city):
    wh_dict = {}  # 大仓编码 -> {原料id...}
    wh_city_dict = {}  # 大仓编码,城市名称 -> {原料id...}
    for line in open('data/1/new_promo.txt'):
        cols = line.strip().split('\t')
        date_str, wh, city, mid, is_main, rebate, total_qty = cols

        wh_dict[wh] = wh_dict.get(wh, set()).add(mid)

        key = ','.join([wh, city])
        wh_city_dict[key] = wh_city_dict.get(key, set()).add(mid)
        pass

    wh_set = wh_dict.get(wh, set())  # 大区维度
    wh_city_set = wh_city_dict.get(','.join([wh, city]), set())  # 城市维度

    mid_ls = []
    if len(wh_set & wh_city_dict) == 0:
        mid_ls.extend(list(wh_set | wh_city_set))
    else:
        mid_ls.extend(list(wh_set))

    # 大仓编码 城市名称 原料id
    return [(wh, city, i) for i in mid_ls]


# 干仓预留库存配置
# noinspection SqlDialectInspection
def loadReserveInvConf():
    sql = """
        SELECT
          t.warehouse, -- 大仓编码
          t.ip_addr, -- url ip
          t.ip_port, -- 端口号
          t.system_info -- 系统标识
        FROM master_wms_ip_config t
        WHERE warehouse IN (
          -- 大仓列表
          SELECT t.id AS wh -- 大仓编码
          FROM master_warehouse t
          WHERE type = 'ZC' AND delete_flag = FALSE
        )
    """
    getQueryData(sql)
    pass


# 干仓预留库存
def doReserveInv():
    # curl -H "Content-type=application/json" http://10.10.68.11/cgi-bin/kcglMgr/atpDcCrdKcs.asp
    url_fix = '/cgi-bin/kcglMgr/atpDcCrdKcs.asp'
    header = {'Content-type': 'application/json'}
    for line in open('data/1/reserve_inv_conf.txt'):
        cols = line.strip().split('\t')
        wh, url = cols[0:2]  # 大仓编码 url
        url += url_fix
        try:
            request = urllib2.Request(url, headers=header)
            response = urllib2.urlopen(request)
            result = json.loads(response.read())
            ls = ['%s\t%s\t%s' % (wh, i["material_id"], i["sl"]) for i in result['datas']]
            for item in ls:
                # 大仓编码 原料id 预留库存
                print(item)
        except Exception as e:
            logger.exception("doReserveInv error")
        pass
    pass


# 算法核心 微仓原料应有
# noinspection SqlDialectInspection
def loadAlgoData():
    sql = """
        SELECT
          vc  AS warehouse_id, -- 微仓编码
          mid AS material_id, -- 原料id
          yb  AS shouldbe_qty -- 应有数量
        FROM wh_material_info;
    """
    getQueryData(sql, conn_name='bi')
    pass


# 活动微仓,待补货微仓,此数据将作为补货的基础数据
# noinspection SqlDialectInspection
def loadActiveVc():
    sql = """
        SELECT
          t.warehouse AS id, -- 大仓编码
          w.city      AS city, -- 城市名称
          w.name      AS name -- 微仓名称
        FROM
          (
            SELECT DISTINCT o.warehouse_code AS warehouse
            FROM oms_order o
            WHERE
              o.pay_time >= date_sub(curdate(), INTERVAL 1 DAY)
              AND o.pay_time < date_add(curdate(), INTERVAL 1 DAY)
              AND o.warehouse_code LIKE '%-%'
          ) t JOIN master_warehouse w
            ON t.warehouse = w.id
               AND w.type = 'WC'
               AND w.delete_flag = FALSE
               AND (w.is_lian_suo_dian IS NULL OR w.is_lian_suo_dian = FALSE)
        ORDER BY t.warehouse DESC
    """
    getQueryData(sql)
    pass


# 微仓本阜、外阜 订单量
# noinspection SqlDialectInspection
def loadVcLocalOuter():
    sql = """
        SELECT
          a.vc, -- 微仓编码
          a.city, -- 城市名称
          a.name, -- 微仓名称
          b.value, -- 本阜、外阜标记
          c.qty -- 订单量
        FROM
          (
            -- 在售微仓
            SELECT
              t.warehouse AS vc, -- 微仓编码
              w.city      AS city, -- 城市
              w.name      AS name -- 微仓名称
            FROM (
                   -- 昨天到现在的订单
                   SELECT DISTINCT o.warehouse_code AS warehouse -- 微仓编码
                   FROM
                     oms_order o
                   WHERE
                     o.pay_time >= curdate()
                     AND o.pay_time < date_add(curdate(), INTERVAL 1 DAY)
                     AND o.warehouse_code LIKE '%-%'
                 ) t, master_warehouse w
            WHERE t.warehouse = w.id
                  AND w.type = 'WC' -- 微仓标识
                  AND (w.is_lian_suo_dian IS NULL OR w.is_lian_suo_dian = FALSE)
                  AND (w.delete_flag = FALSE)
            ORDER BY vc DESC
          ) a LEFT JOIN (
                          -- 本阜、外阜标记
                          SELECT
                            t.warehouse_id, -- 微仓编码
                            t.city, -- 城市名称
                            t.value -- 本埠:BF 外阜:WF
                          FROM psm_rule_map t
                          WHERE t.del_flag = FALSE
                                AND t.type = 'benfuWaifu'
                        ) b ON a.city = b.city
          LEFT JOIN (
                      -- 订单量
                      SELECT
                        t.warehouse_code AS warehouse, -- 微仓编码
                        count(1)         AS qty -- 订单量
                      FROM
                        oms_order t
                      WHERE
                        t.pay_time > date_sub(curdate(), INTERVAL 1 DAY)
                        AND t.pay_time < date_add(curdate(), INTERVAL 1 DAY)
                        AND t.order_type = 10
                        AND t.`status` <> 40
                        AND t.warehouse_code IS NOT NULL
                      GROUP BY t.warehouse_code
                    ) c ON a.vc = c.warehouse;
    """
    getQueryData(sql)
    pass


# 大仓中外阜微仓占比
def doWhOuterRatio():
    for wh, lines in groupby(open('data/1/vc_local_outer.txt'), key=lambda x: x.split('\t')[0].split('-')[0]):
        out_order = 0  # 外阜订单数量
        out_num = 0  # 外阜微仓数量
        total_order = 0  # 总订单
        total_num = 0  # 微仓总数量
        for line in lines:
            cols = line.strip().split('\t')
            # 微仓编码 城市名称 微仓名称 本阜、外阜标记 订单量
            vc, city, vc_name, outer_flag, sale = cols
            if outer_flag == 'WF':
                out_num += 1
                out_order += int(sale)
            total_order += int(sale)
            total_num += 1
        ratio = float(out_order) / float(total_order)  # 外阜比例
        if ratio == 0:
            ratio = out_num / total_num
        ls = [wh, ratio]
        print('\t'.join(map(str, ls)))
    pass


# 微仓 本阜、外阜 品类 订单量
# noinspection SqlDialectInspection
def loadVcLocalOuterCate():
    sql = """
        SELECT
          a.vc, -- 微仓编码
          a.city, -- 城市名称
          a.name, -- 微仓名称
          b.value, -- 本阜、外阜标记
          c.category, -- 品类
          c.qty -- 销量
        FROM
          (
            -- 在售微仓
            SELECT
              t.warehouse AS vc, -- 微仓编码
              w.city      AS city, -- 城市
              w.name      AS name -- 微仓名称
            FROM (
                   -- 昨天到现在的订单
                   SELECT DISTINCT o.warehouse_code AS warehouse -- 微仓编码
                   FROM
                     oms_order o
                   WHERE
                     o.pay_time >= curdate()
                     AND o.pay_time < date_add(curdate(), INTERVAL 1 DAY)
                     AND o.warehouse_code LIKE '%-%'
                 ) t, master_warehouse w
            WHERE t.warehouse = w.id
                  AND w.type = 'WC' -- 微仓标识
                  AND (w.is_lian_suo_dian IS NULL OR w.is_lian_suo_dian = FALSE)
                  AND (w.delete_flag = FALSE)
            ORDER BY vc DESC
          ) a LEFT JOIN (
                          -- 本阜、外阜标记
                          SELECT
                            t.warehouse_id, -- 微仓编码
                            t.city, -- 城市名称
                            t.value -- 本埠:BF 外阜:WF
                          FROM psm_rule_map t
                          WHERE t.del_flag = FALSE
                                AND t.type = 'benfuWaifu'
                        ) b ON a.city = b.city
          LEFT JOIN (
                      -- 最近7天品类销量
                      SELECT
                        t.warehouse_code as vc, -- 微仓编码
                        t.category, -- 品类
                        ROUND(avg(t.qty), 0) AS qty
                      FROM psm_riqi_cangku_pinlei_xiaoliang t
                      WHERE batch < curdate() AND batch >= date_sub(curdate(), INTERVAL 8 DAY)
                      GROUP BY t.category, vc
                    ) c ON a.vc = c.vc
    """
    getQueryData(sql)
    pass


# 大仓中外阜品类比例
def doWhOuterCateRatio():
    for wh, group in groupby(open('data/1/vc_local_outer_cate.txt'), key=lambda x: x.split('\t')[0].split('-')[0]):
        outer = {}
        total = {}
        for line in group:
            cols = line.strip().split('\t')
            # 微仓编号 城市名称 微仓名称 外阜标记 品类 销量
            vc, city, vc_name, outer_flag, cate, sale = cols
            key = cate
            if outer_flag == 'WF':
                outer[key] = outer.get(key, 0) + float(sale)
            total[key] = total.get(key, 0) + float(sale)

        for cate in total.iterkeys():
            ratio = outer.get(cate, 0.0) / total.get(cate, float(len(total)))
            ls = [wh, cate, ratio]
            print('\t'.join(map(str, ls)))
        pass
    pass


# 在售列表
# noinspection SqlDialectInspection
def loadOnlineMid():
    wh_ls = open('data/1/active_wh.txt').readlines()
    wh_ls_str = "','".join(map(lambda x: x.strip(), wh_ls))
    sql = """
        SELECT DISTINCT
          mcw.warehouse, -- 大仓编码
          m.materials_id, -- 原料id
        FROM master_category c
          JOIN master_category_sku s ON c.category_id = s.category_id AND c.is_chrome = TRUE AND c.active = TRUE
          JOIN master_bom b ON s.sku_id = b.sku_id
          JOIN master_materials m ON b.materials_id = m.materials_id
          JOIN bms_product bp ON bp.goods_no = b.sku_id AND bp.goods_no = b.sku_id AND bp.goods_status = 1
          JOIN master_category_warehouse mcw ON c.category_id = mcw.category_id AND mcw.is_liansuodian = FALSE
            AND mcw.warehouse in ('{wh_ls_str}')
        ORDER BY mcw.warehouse,m.category, m.materials_id
    """.format(wh_ls_str=wh_ls_str)
    getQueryData(sql)
    pass


# 获取微仓信息
def getVcInfo():
    # 微仓信息
    vc_dict = {}  # 微仓编号 -> 城市名称
    for line in open('data/1/vc_info.txt'):
        cols = line.strip().split('\t')
        # 仓库编号 仓库名称 warehouse_live 仓库类型 连锁店 省名称 城市名称
        vc, name, warehouse_live, vc_type, isliansuodian, provice, city = cols
        vc_dict[vc] = city
    return vc_dict


# 获取新品促销品信息
def getNewPromoInfo():
    # 新品促销品
    promo_dict = {}  # 大仓编码 -> list
    promo_city_dict = {}  # 大仓编码,城市 -> list
    for line in open('data/1/new_promo.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 城市 原料id 品类 原料名称 周转天数 温区 is_main, rebate, total_qty
        wh, city, mid, cate, name, turnover, store, is_main, rebate, total_qty = cols
        promo_dict[wh] = promo_dict.get(wh, [])
        promo_dict[wh].append([wh, mid, cate, name, turnover, store])

        key = ','.join([wh, city])
        promo_dict[key] = promo_dict.get(key, [])
        promo_dict[key].append([wh, mid, cate, name, turnover, store])
    return promo_dict


# AS在线原料信息
def getAsOnlineMidInfo():
    as_online_dict = {}  # 在售清单 大仓编码 -> list
    # AS在售清单
    for wh, group in groupby(open('data/1/online_mid.txt'), key=lambda x: x.split('\t')[0]):
        ls = []
        for line in group:
            cols = line.strip().split('\t')
            # 大仓编码 原料id 品类 原料名称 周转天数 温区
            _, mid, cate, name, turnover, store = cols
            ls.append([wh, mid, cate, name, turnover, store])
        as_online_dict[wh] = ls
    return as_online_dict


# 处理在售列表
def doOnlineMid():
    vc_dict = getVcInfo()  # 获取微仓信息: 微仓编码 ->城市名称
    promo_dict = getNewPromoInfo()  # 大仓编码 -> list
    as_online_dict = getAsOnlineMidInfo()  # 获取AS在线列表

    # 待补货微仓列表
    for line in open('data/1/active_vc.txt'):
        cols = line.strip().split('\t')
        vc, city, name = cols
        wh = vc.split('-')[0]  # 大仓编码

        as_online_ls = as_online_dict[wh]  # 大仓在线清单
        as_set = set([i[1] for i in as_online_ls])

        # """
        promo_ls = promo_dict.get(vc, [])  # 促销列表
        promo_city_ls = promo_dict.get(','.join([vc, city]), [])  # 城市维度促销列表

        # 处理促销品
        if len(promo_ls) > 0 and len(promo_city_ls) > 0:
            x = set([i[1] for i in promo_ls]) & set([j[1] for j in promo_city_ls])  # 交集
            if len(x) == 0:
                promo_ls.extend(promo_city_ls)
            pass

        # 添加促销品
        if len(promo_ls) > 0:
            for item in promo_ls:
                mid = item[1]
                if mid not in as_set:
                    as_online_ls.append(item)
                pass
            pass
        # """

        for item in as_online_ls:
            print('\t'.join(item[0:1] + [vc] + item[1:]))
        pass

    pass


# 补货批次
# noinspection SqlDialectInspection
def loadBatchHourConf():
    sql = """
        SELECT
          id,
          type,
          material_id, -- 原料id
          bch2,
          material_shelflife,
          store_condition_code,
          category_id,
          warehouse_id, -- 微仓编号
          warehouse_live,
          benfu_waifu,
          city,
          daqu,
          `value`,
          shelf_life,
          create_by,
          create_date,
          update_by,
          update_date,
          remarks,
          del_flag
        FROM psm_rule_map
        WHERE type = 'buhuoPici' AND del_flag = FALSE
    """
    getQueryData(sql)
    pass


# buhuoPici
# select * from psm_rule_map where type='buhuoPici' and del_flag=FALSE
# COL.MATERIAL_ID, COL.STORE_CONDITION, COL.CATEGORY_ID, COL.BCH2, COL.BENFU_WAIFU, COL.DAQU
# BENFU_WAIFU DAQU MATERIAL_ID BCH2 STORE_CONDITION CATEGORY_ID
# CATEGORY_ID STORE_CONDITION BCH2 MATERIAL_ID DAQU BENFU_WAIFU
# 品类 温区 拣货批次 原料id 大仓 外阜标记
# @todo 能量算法


# 批次字典
def doBatchDict():
    batch_dict = {}  # 批次字典
    for line in open('data/1/batch_conf.txt'):
        cols = line.rstrip().split('\t')
        # 品类 存储温区 拣货批次 原料id 大仓编码 外部标记 批次时间(小时)
        cate, store, bch2, mid, wh, outer, hour = cols
        cate = 'cate' if cate == '' else cate
        store = 'store' if store == '' else store
        bch2 = 'bch2' if bch2 == '' else bch2
        mid = 'mid' if mid == '' else mid
        wh = 'wh' if wh == '' else wh
        outer = 'outer' if outer == '' else outer
        hour = 'hour' if hour == '' else hour

        # 建立倒序字典树
        batch_dict[outer] = batch_dict.get(outer, {})
        sub_dict = batch_dict[outer]

        sub_dict[wh] = sub_dict.get(wh, {})
        sub_dict = sub_dict[wh]

        sub_dict[mid] = sub_dict.get(mid, {})
        sub_dict = sub_dict[mid]

        sub_dict[bch2] = sub_dict.get(bch2, {})
        sub_dict = sub_dict[bch2]

        sub_dict[store] = sub_dict.get(store, {})
        sub_dict = sub_dict[store]

        sub_dict[cate] = sub_dict.get(cate, hour)

        # batch_dict[cate] = batch_dict.get(cate, {})
        # sub_dict = batch_dict[cate]
        #
        # sub_dict[store] = sub_dict.get(store, {})
        # sub_dict = sub_dict[store]
        #
        # sub_dict[bch2] = sub_dict.get(bch2, {})
        # sub_dict = sub_dict[bch2]
        #
        # sub_dict[mid] = sub_dict.get(mid, {})
        # sub_dict = sub_dict[mid]
        #
        # sub_dict[wh] = sub_dict.get(wh, {})
        # sub_dict = sub_dict[wh]
        #
        # sub_dict[outer] = sub_dict.get(outer, hour)
    print(json.dumps(batch_dict))


# 加载微仓批次时间
def loadVcBatchInfo():
    # 微仓详情
    vc_dict = {}  # 微仓编号 -> 详情
    for line in open('data/1/vc_info.txt'):
        cols = line.strip().split('\t')
        # 仓库编号 仓库名称 warehouse_live 仓库类型 连锁店 省名称 城市名称
        vc, name, warehouse_live, vc_type, isLianSuoDian, provice, city = cols
        vc_dict[vc] = cols

    # 外阜规则
    OutRuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/vc_outer_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        OutRuleMapDict[key] = rule

    # 批次时间
    BatchRuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/batch_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        BatchRuleMapDict[key] = rule

    # 活动微仓
    active_vc_dict = {}  # vc -> 详情
    for line in open('data/1/active_vc.txt'):
        cols = line.strip().split('\t')
        vc, city, name = cols
        wh = vc.split('-')[0]  # 大仓编码
        active_vc_dict[vc] = cols
        bch2 = getStoreBatch(vc, None, None, None, None)  # 拣货批次
        warehouse_live = vc_dict.get(vc)[2]
        # 外阜标记
        outer = getValueFromMapRuleCore('benfuWaifu', vc, warehouse_live, None, city,
                                        wh, None, None, None, None, bch2, OutRuleMapDict
                                        )[0]
        # 发单批次
        batch_hour = getValueFromMapRuleCore('buhuoPici', vc, warehouse_live, outer, city,
                                             wh, None, None, None, None, bch2, BatchRuleMapDict
                                             )[0]
        print('\t'.join([vc, batch_hour]))
    pass


# 微仓外阜标记
def loadVcOuter():
    # 微仓详情
    vc_dict = {}  # 微仓编号 -> 详情
    for line in open('data/1/vc_info.txt'):
        cols = line.strip().split('\t')
        # 仓库编号 仓库名称 warehouse_live 仓库类型 连锁店 省名称 城市名称
        vc, name, warehouse_live, vc_type, isLianSuoDian, provice, city = cols
        vc_dict[vc] = cols

    # 外阜规则
    OutRuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/vc_outer_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        OutRuleMapDict[key] = rule

    # 活动微仓
    active_vc_dict = {}  # vc -> 详情
    for line in open('data/1/active_vc.txt'):
        cols = line.strip().split('\t')
        vc, city, name = cols
        wh = vc.split('-')[0]  # 大仓编码
        active_vc_dict[vc] = cols
        bch2 = getStoreBatch(vc, None, None, None, None)  # 拣货批次
        warehouse_live = vc_dict.get(vc)[2]
        # 外阜标记
        outer = getValueFromMapRuleCore('benfuWaifu', vc, warehouse_live, None, city,
                                        wh, None, None, None, None, bch2, OutRuleMapDict
                                        )[0]
        print('\t'.join([vc, outer]))
    pass


# 获取批次小时
def getBatchHour(cate, store, bch2, mid, wh, outer):
    """
    获取批次小时数
    :param cate: 品类
    :param store: 温区
    :param bch2: 拣货批次
    :param mid: 原料id
    :param wh: 大仓
    :param outer: 外阜标记
    :return:
    """
    cate = 'cate' if cate == '' else cate
    store = 'store' if store == '' else store
    bch2 = 'bch2' if bch2 == '' else bch2
    mid = 'mid' if mid == '' else mid
    wh = 'wh' if wh == '' else wh
    outer = 'outer' if outer == '' else outer
    batch_dict = json.loads(open('data/1/batch_dict_json.txt').read())  # 批次字典
    batch_hour = batch_dict[cate][store][bch2][mid][wh][outer]  # 批次小时
    return batch_hour


# 微仓详情
# noinspection SqlDialectInspection
def loadVcInfo():
    sql = """
        SELECT
          t.id, -- 仓库编号
          t.name, -- 仓库名称
          t.warehouse_live,
          t.type, -- 仓库类型 大仓:ZC 微仓:WC
          t.is_lian_suo_dian,
          t.province, -- 省
          t.city -- 城市
        FROM master_warehouse t;
    """
    getQueryData(sql)
    pass


# 原料详情
# noinspection SqlDialectInspection
def loadMidInfo():
    sql = """
        SELECT
          internal_id, -- 原料id
          `name`, -- 原料名称
          category_id, -- 品类id
          store_condition, -- 存储温区
          parent_category_name, -- 一级品类名称
          shelf_life, -- 保质期
          unit_type, -- 单位
          remark, -- 标记
          is_short_life, -- 是否短保
          is_scantling, -- 是否标品
          shelf_life_hour -- 保质期小时
        FROM bms_material;
    """
    getQueryData(sql)
    pass


# 原料周转天数
# noinspection SqlDialectInspection
def loadMidTurnover():
    sql = """
        SELECT
          materials_id, -- 原料id
          turnover_days -- 周转天数
        FROM master_materials;
    """
    getQueryData(sql)
    pass


# 原料周转配置
# noinspection SqlDialectInspection
def loadMidTurnoverConf():
    sql = """
        SELECT
          id,
          type,
          material_id, -- 原料id
          bch2,
          material_shelflife,

          store_condition_code,
          category_id,
          warehouse_id, -- 微仓编号
          warehouse_live,
          benfu_waifu,

          city,
          daqu,
          `value`,
          shelf_life,
          create_by,

          create_date,
          update_by,
          update_date,
          remarks,
          del_flag
        FROM psm_rule_map
        WHERE type = 'yuanliaoZhouzhuantianshu'
              AND del_flag = FALSE
    """
    getQueryData(sql)
    pass


# 微仓外阜标记
# noinspection SqlDialectInspection
def loadVcOuterConf():
    sql = """
        SELECT
          id,
          type,
          material_id, -- 原料id
          bch2,
          material_shelflife,

          store_condition_code,
          category_id,
          warehouse_id, -- 微仓编号
          warehouse_live,
          benfu_waifu,

          city,
          daqu,
          `value`,
          shelf_life,
          create_by,

          create_date,
          update_by,
          update_date,
          remarks,
          del_flag
        FROM psm_rule_map
        WHERE type = 'benfuWaifu' AND del_flag = FALSE
    """
    getQueryData(sql)
    pass


# 获取拣货批次
def getStoreBatch(daqu, category, storeCondition, shelfLife, shelfLifeHour):
    """
    获取拣货批次
    :param daqu: 大仓编码\微仓编码
    :param category: 品类名称
    :param storeCondition: 存储温区
    :param shelfLife: 保质期
    :param shelfLifeHour: 保质期小时
    :return:
    """
    QITA = "其它"
    DONGPIN = "冻品"
    GANCANG = "干仓"
    GUOSHU = "果蔬"
    if daqu is None:
        return QITA
    daqu = daqu.split('-')[0]

    if 'MRYXSZ' == daqu:
        if 'FREEZE' == storeCondition:
            return DONGPIN
        if "水果" == category or "蔬菜" == category:
            return GUOSHU
        return QITA

    if storeCondition is not None and 'FREEZE' == storeCondition:
        return DONGPIN

    if daqu not in {'MRYXTJ', 'MRYXBJN'}:
        return QITA

    shuiguoshucai = False
    if category is not None and ("水果" in category or "蔬菜" in category):
        shuiguoshucai = True

    baozhiqi = int(shelfLife) if shelfLife is not None and shelfLife != 'None' else 0
    if shelfLifeHour is not None and shelfLifeHour > 0:
        baozhiqi += 1

    if shuiguoshucai is not None and baozhiqi > 30 and 'ROOM' == storeCondition:
        return GANCANG
    return QITA


# 处理批次数据 补货的基础数据
def doBatch():
    # (1) 在售列表
    online_mid_dict = {}  # 在售卖原料列表  大仓编码->{mid,mid...}
    # 在售原料列表
    for line in open('data/1/online_mid.txt'):
        cols = line.rstrip().split('\t')
        # 大仓编码 原料ID 品类 原料名称 周转 存储温区
        wh, mid, cate, mid_name, trunover, store = cols

        mid_set = online_mid_dict.get(wh, set())
        mid_set.add(mid)
        online_mid_dict[wh] = mid_set
    pass

    # (2) 微仓详情
    vc_info = {}  # 微仓详情 微仓编号 -> 微仓详情
    for line in open('data/1/vc_info.txt'):
        cols = line.rstrip().split('\t')
        # 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = cols
        if type_str == 'WC':
            vc_info[vc] = cols
        pass

    # (3) 外阜标记
    vc_outer = {}  # 外阜标记 城市名称 -> 外阜标记
    for line in open('data/1/vc_outer.txt'):
        cols = line.rstrip().split('\t')
        # 原料id 城市名称 外阜标记
        mid, city, flag = cols
        vc_outer[city] = flag
        pass

    # (4) 新品促销品
    new_promo_info = {}
    for line in open('data/1/new_promo.txt'):
        cols = line.rstrip().split('\t')
        # 大仓编码 城市 原料id 品类 原料名称 周转期 温区
        wh, city, mid, cate, mid_name, turnover, store = cols
        ls = new_promo_info.get(wh, [])
        ls.append(cols)
        new_promo_info[wh] = ls
        pass

    # (5) 原料详情
    mid_dict = {}  # 原料详情 mid -> []
    for line in open('data/1/mid_info.txt'):
        cols = line.strip().split('\t')
        # 原料id 原料名称 分类id 温区 分类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
        mid, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = cols
        mid_dict[mid] = cols
        pass

    # 批次时间
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/batch_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule
        pass

    # 待补货的微仓
    for line in open('data/1/active_vc.txt'):
        # 待补货的微仓
        cols = line.rstrip().split('\t')
        # 微仓编号 城市名称 微仓名称
        vc, city, vc_name = cols
        wh = vc.split('-')[0]  # 大仓编码

        online_mid_set = online_mid_dict[wh]  # 在线商品列表
        # 新品促销品
        if wh in new_promo_info:
            new_promo_ls = new_promo_info[wh]
            new_promo_midset = set([i[2] for i in new_promo_ls])  # 新品促销品原料set
            online_mid_set = online_mid_set | new_promo_midset  # 追加新品促销品

        # 补全数据
        batch_list = []
        for mid in online_mid_set:
            # 原料id 原料名称 分类id 温区 分类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
            mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = mid_dict[mid][
                                                                                                        1:]
            # 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
            vc_code, vc_name, warehouse_live, type_str, is_lian_suo_dian, province, city = vc_info[vc]
            # 拣货批次
            bch2 = getStoreBatch(wh, cate_name, store, sl, sl_hour)
            # 外阜
            outer = vc_outer.get(city, 'BF')
            # 批次
            batch_hour = getValueFromMapRuleCore('buhuoPici', vc, warehouse_live, outer, city, wh, mid, sl, store,
                                                 cate_name, bch2, RuleMapDict)[0]  # todo 批次时间 能量算法
            ls = [wh, vc, warehouse_live, outer, city, mid, cate_name, store, sl, sl_hour, bch2, batch_hour]
            print('\t'.join(map(str, ls)))
        pass
    pass


# 如果有手动推单则剔除 @todo 剔除手动推单


# 大仓系数
# noinspection SqlDialectInspection
def loadWhParam():
    sql = """
        SELECT
          t.warehouse, -- 大仓编码
          t.proportion -- 系数
        FROM psm_buhuo_para t
        WHERE warehouse NOT like '%-%'
          AND type = 1
          AND t.period_start <= curdate()
          AND t.period_end >= curdate()
    """
    getQueryData(sql)
    pass


# 微仓系数
# noinspection SqlDialectInspection
def loadVcParam():
    sql = """
        SELECT
          t.warehouse, -- 微仓编码
          t.proportion -- 系数
        FROM psm_buhuo_para t
        WHERE warehouse like '%-%' AND type = 1
          AND t.period_start <= curdate()
          AND t.period_end >= curdate()
    """
    getQueryData(sql)
    pass


# 微仓七日平均销量
# noinspection SqlDialectInspection
def loadVcWeekSale():
    sql = """
        SELECT
          t.warehouse, -- 微仓编号
          avg(t.qty) -- 平均销量
        FROM psm_riqi_cangku_xiaoliang t
        WHERE batch >= date_sub(curdate(), INTERVAL 7 DAY)
              AND batch < curdate()
              AND warehouse LIKE '%-%'
        GROUP BY warehouse;
    """
    getQueryData(sql)
    pass


# 微仓明日星期平均销量
# noinspection SqlDialectInspection
def loadVcTomorowWeekSale():
    sql = """
        SELECT
          t.warehouse, -- 微仓编号
          avg(t.qty) -- 平均销量
        FROM psm_riqi_cangku_xiaoliang t
        WHERE batch IN (
          date_add(curdate(), INTERVAL 1 - 1 * 7 DAY),
          date_add(curdate(), INTERVAL 1 - 2 * 7 DAY),
          date_add(curdate(), INTERVAL 1 - 3 * 7 DAY),
          date_add(curdate(), INTERVAL 1 - 4 * 7 DAY)
        ) AND warehouse like '%-%'
        GROUP BY warehouse
    """
    getQueryData(sql)
    pass


# 计算明日占销量比
def doTomorowRatio():
    vc_sale_dict = {}  # 七日平均销量
    for line in open('data/1/vc_week_sale.txt'):
        cols = line.strip().split('\t')
        # 微仓编号 七日平均销量
        vc, value = cols
        vc_sale_dict[vc] = float(value)

    vc_tomorrow_sale = {}  # 明日星期销量
    for line in open('data/1/vc_tommorow_week_sale.txt'):
        cols = line.strip().split('\t')
        # 微仓编号 星期x平均销量
        vc, value = cols
        vc_tomorrow_sale[vc] = float(value)

    for vc, sale in vc_sale_dict.iteritems():
        tomorrow_sale = vc_tomorrow_sale.get(vc, 1.0)
        ratio = tomorrow_sale / sale  # 明日占比
        ratio = min(ratio, 1.3)  # 设置上限
        ratio = max(ratio, 0.8)  # 设置下限
        ls = [vc, ratio]
        print('\t'.join(map(str, ls)))

    pass


# 微仓前四个周x的品类平均
def loadVcCateWeekAvg():
    sql = """
        SELECT
          warehouse_code, -- 微仓编码
          category, -- 品类
          AVG(qty) avg_qty -- 平均值
        FROM
          psm_riqi_cangku_pinlei_xiaoliang t
        WHERE warehouse_code like '%-%' AND  batch IN (
          date_sub(curdate(), INTERVAL 7 - 1 DAY),
          date_sub(curdate(), INTERVAL 2 * 7 -1 DAY),
          date_sub(curdate(), INTERVAL 3 * 7 -1 DAY),
          date_sub(curdate(), INTERVAL 4 * 7 -1 DAY)
        )
        GROUP BY warehouse_code,category
        ORDER BY warehouse_code,category
    """
    getQueryData(sql)


# 黑名单
# noinspection SqlDialectInspection
# makeMap(COL.MATERIAL_ID, COL.STORE_CONDITION, COL.CATEGORY_ID, COL.WAREHOUSE_ID, COL.CITY, COL.DAQU);
# @todo 能量算法
def loadBlackMidConf():
    sql = """
        SELECT
          t.id,
          t.type,
          t.material_id, -- 原料id
          t.bch2,
          t.material_shelflife,
          t.store_condition_code,
          t.category_id,
          t.warehouse_id, -- 微仓编号
          t.warehouse_live,
          t.benfu_waifu,
          t.city,
          t.daqu,
          t.value,
          t.shelf_life,
          t.create_by,
          t.create_date,
          t.update_by,
          t.update_date,
          t.remarks,
          t.del_flag
        FROM psm_rule_map t
        WHERE t.type = 'buhuoHeimingdan' AND del_flag = FALSE
    """
    getQueryData(sql)
    pass


# 计算黑名单
def doBlackMid():
    # 微仓信息
    vc_dict = {}  # 微仓详情 微仓编号 -> 微仓详情
    for line in open('data/1/vc_info.txt'):
        cols = line.rstrip().split('\t')
        # 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = cols
        if type_str == 'WC':
            vc_dict[vc] = cols
        pass

    # 原料信息
    mid_dict = {}  # mid -> []
    for line in open('data/1/mid_info.txt'):
        cols = line.strip().split('\t')
        # 原料id 原料名称 分类id 温区 分类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
        mid, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = cols
        mid_dict[mid] = cols

    # 外阜标记
    vc_outer_dict = {}
    for line in open('data/1/vc_outer.txt'):
        cols = line.strip().split('\t')
        vc, city, flag = cols
        vc_outer_dict[vc] = flag

    # 黑名单规则
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/black_mid_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule

    # 在售列表
    for line in open('data/1/vc_online_mid.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
        wh, vc, mid, cate, name, trunover, store = cols
        _, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = mid_dict[mid]
        if vc in vc_dict:
            vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = vc_dict[vc]
            outer = vc_outer_dict.get(vc, 'BF')
            bch2 = getStoreBatch(vc, cate, store, sl, sl_hour)  # 拣货批次
            flag = getValueFromMapRuleCore('buhuoHeimingdan', vc, warehouse_live, outer, city,
                                           wh, mid, sl, store, cate, bch2, RuleMapDict
                                           )[0]
            if flag == 'true':
                print('\t'.join([wh, vc, mid, flag]))
        else:
            pass
    pass


# 辅料不补货 sub_mid.txt
# 获取大仓库存
# curl -H "Content-Type: application/json" -X POST -d '{"warehouse":"MRYXTJ-WANGJING","outer_ids":["p-HBhnmg-1g"]}' http://172.16.30.79:18001/atp/getATP.json
# 大仓无库存不补货


# 新明日占比
# 大规格补货 @todo 能量算法
# 现有库存 ATP库存
#

# 今日销量
# noinspection SqlDialectInspection
def loadTodaySale():
    sql = """
        SELECT
          t.warehouse, -- 微仓编号
          t.material_id, -- 原料id
          t.sales_data -- 销售量
        FROM psm_sales_data t
        WHERE batch = curdate()
    """
    getQueryData(sql)
    pass


# 最大补货数量 @todo 能量算法
# noinspection SqlDialectInspection
def loadBigUnitConf():
    sql = """
        SELECT
          t.id,
          t.type,
          t.material_id, -- 原料id
          t.bch2,
          t.material_shelflife,
          t.store_condition_code,
          t.category_id,
          t.warehouse_id, -- 微仓编号
          t.warehouse_live,
          t.benfu_waifu,
          t.city,
          t.daqu,
          t.value,
          t.shelf_life,
          t.create_by,
          t.create_date,
          t.update_by,
          t.update_date,
          t.remarks,
          t.del_flag
        FROM psm_rule_map t
        WHERE t.type = 'daGuigeBuhuo' AND del_flag = FALSE
    """
    getQueryData(sql)


# 最加大规格
def doBatchBigUnit():
    # 大规格
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/big_unit_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule

    for line in open('data/1/batch.txt'):
        cols = line.rstrip().split('\t')
        wh, vc, warehouse_live, outer, city, mid, cate_name, store, sl, sl_hour, bch2, batch_hour = cols
        big_unit = getValueFromMapRuleCore('buhuoPici', vc, warehouse_live, outer, city, wh, mid, sl, store,
                                           cate_name, bch2, RuleMapDict)[0]  # todo 批次时间 能量算法
        ls = [wh, vc, warehouse_live, outer, city, mid, cate_name, store, sl, sl_hour, bch2, batch_hour, big_unit]
        print('\t'.join(map(str, ls)))
    pass


# 计算大规格
def doVcMidBigUnit():
    # 微仓信息
    vc_dict = {}  # 微仓详情 微仓编号 -> 微仓详情
    for line in open('data/1/vc_info.txt'):
        cols = line.rstrip().split('\t')
        # 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = cols
        if type_str == 'WC':
            vc_dict[vc] = cols
        pass

    # 原料信息
    mid_dict = {}  # mid -> []
    for line in open('data/1/mid_info.txt'):
        cols = line.strip().split('\t')
        # 原料id 原料名称 分类id 温区 分类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
        mid, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = cols
        mid_dict[mid] = cols

    # 外阜标记
    vc_outer_dict = {}
    for line in open('data/1/vc_outer.txt'):
        cols = line.strip().split('\t')
        vc, city, flag = cols
        vc_outer_dict[vc] = flag

    # 大规格规则
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/big_unit_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule

    # 在售列表
    for line in open('data/1/vc_online_mid.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
        wh, vc, mid, cate, name, trunover, store = cols
        _, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = mid_dict[mid]
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = vc_dict[vc]
        outer = vc_outer_dict[vc]
        bch2 = getStoreBatch(vc, cate, store, sl, sl_hour)  # 拣货批次
        big_unit = getValueFromMapRuleCore('daGuigeBuhuo', vc, warehouse_live, outer, city,
                                           wh, mid, sl, store, cate, bch2, RuleMapDict
                                           )[0]
        if big_unit is not None and big_unit != '':
            print('\t'.join([wh, vc, mid, big_unit]))
    pass


# 微仓原料数据整理
def doVcInvCollect():
    # 在售列表
    for vc, group in groupby(open('data/1/vc_online_mid.txt'), key=lambda x: x.split('\t')[1]):
        mid_set = set()
        for line in group:
            cols = line.strip().split('\t')
            # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
            wh, vc, mid, cate, name, trunover, store = cols
            mid_set.add(mid)
        for mid in mid_set:
            print('\t'.join([vc, mid]))
    pass


# 大仓原料数据整理
def doWhInvCollect():
    # 在售列表
    for wc, group in groupby(open('data/1/vc_online_mid.txt'), key=lambda x: x.split('\t')[0]):
        mid_set = set()
        for line in group:
            cols = line.strip().split('\t')
            # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
            wh, vc, mid, cate, name, trunover, store = cols
            mid_set.add(mid)
        for mid in mid_set:
            print('\t'.join([wc, mid]))
    pass


# 最大补货数量
# noinspection SqlDialectInspection
def loadMaxSupplyConf():
    sql = """
        SELECT
          t.id,
          t.type,
          t.material_id, -- 原料id
          t.bch2,
          t.material_shelflife,
          t.store_condition_code,
          t.category_id,
          t.warehouse_id, -- 微仓编号
          t.warehouse_live,
          t.benfu_waifu,
          t.city,
          t.daqu,
          t.value,
          t.shelf_life,
          t.create_by,
          t.create_date,
          t.update_by,
          t.update_date,
          t.remarks,
          t.del_flag
        FROM psm_rule_map t
        WHERE t.type = 'zuidaBuhuoShuliang' AND del_flag = FALSE
    """
    getQueryData(sql)
    pass


# 追加最大补货数量
def doBatchMaxSupply():
    # 大规格
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/max_supply_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule

    for line in open('data/1/batch_bigUint.txt'):
        cols = line.split('\t')
        wh, vc, warehouse_live, outer, city, mid, cate_name, store, sl, sl_hour, bch2, batch_hour, big_unit = cols
        # 最大补货数量
        max_supply = getValueFromMapRuleCore('zuidaBuhuoShuliang', vc, warehouse_live, outer, city, wh, mid, sl, store,
                                             cate_name, bch2, RuleMapDict)[0]  # todo 批次时间 能量算法
        ls = [wh, vc, warehouse_live, outer, city, mid, cate_name, store, sl, sl_hour, bch2, batch_hour,
              big_unit.strip(), max_supply]
        print('\t'.join(map(str, ls)))
    pass


# 最大补货数量
def doMaxSupply():
    # 微仓信息
    vc_dict = {}  # 微仓详情 微仓编号 -> 微仓详情
    for line in open('data/1/vc_info.txt'):
        cols = line.rstrip().split('\t')
        # 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = cols
        if type_str == 'WC':
            vc_dict[vc] = cols
        pass

    # 原料信息
    mid_dict = {}  # mid -> []
    for line in open('data/1/mid_info.txt'):
        cols = line.strip().split('\t')
        # 原料id 原料名称 分类id 温区 分类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
        mid, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = cols
        mid_dict[mid] = cols

    # 外阜标记
    vc_outer_dict = {}
    for line in open('data/1/vc_outer.txt'):
        cols = line.strip().split('\t')
        vc, city, flag = cols
        vc_outer_dict[vc] = flag

    # 最大补货数量规则
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/max_supply_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule

    # 在售列表
    for line in open('data/1/vc_online_mid.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
        wh, vc, mid, cate, name, trunover, store = cols
        _, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = mid_dict[mid]
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = vc_dict[vc]
        outer = vc_outer_dict[vc]
        bch2 = getStoreBatch(vc, cate, store, sl, sl_hour)  # 拣货批次
        max_supply = getValueFromMapRuleCore('zuidaBuhuoShuliang', vc, warehouse_live, outer, city,
                                             wh, mid, sl, store, cate, bch2, RuleMapDict
                                             )[0]
        if max_supply is not None and max_supply != '':
            print('\t'.join([wh, vc, mid, max_supply]))
    pass


# 原料周转天数系数
def doMidTurnOver():
    # 微仓信息
    vc_dict = {}  # 微仓详情 微仓编号 -> 微仓详情
    for line in open('data/1/vc_info.txt'):
        cols = line.rstrip().split('\t')
        # 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = cols
        if type_str == 'WC':
            vc_dict[vc] = cols
        pass

    # 原料信息
    mid_dict = {}  # mid -> []
    for line in open('data/1/mid_info.txt'):
        cols = line.strip().split('\t')
        # 原料id 原料名称 分类id 温区 分类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
        mid, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = cols
        mid_dict[mid] = cols

    # 外阜标记
    vc_outer_dict = {}
    for line in open('data/1/vc_outer.txt'):
        cols = line.strip().split('\t')
        vc, city, flag = cols
        vc_outer_dict[vc] = flag

    # 原料周转天数规则
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/mid_turnover_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule

    # 在售列表
    for line in open('data/1/vc_online_mid.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
        wh, vc, mid, cate, name, trunover, store = cols
        _, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = mid_dict[mid]
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = vc_dict[vc]
        outer = vc_outer_dict[vc]
        bch2 = getStoreBatch(vc, cate, store, sl, sl_hour)  # 拣货批次
        turnover = getValueFromMapRuleCore('yuanliaoZhouzhuantianshu', vc, warehouse_live, outer, city,
                                           wh, mid, sl, store, cate, bch2, RuleMapDict
                                           )[0]
        if turnover is not None and turnover != '':
            print('\t'.join([wh, vc, mid, turnover]))
    pass


# 商品规格
# noinspection SqlDialectInspection
def loadMidUnit():
    sql = """
        SELECT
          cw.warehouse   AS daqu, -- 大仓编码
          b.materials_id AS material_id, -- 原料id
          b.qty -- 规格
        FROM
          master_category c,
          master_category_sku s,
          master_bom b,
          master_category_warehouse cw,
          bms_product bp
        WHERE
          c.is_chrome = 1
          AND c.active = 1
          AND bp.goods_no = b.sku_id
          AND bp.goods_status = TRUE
          AND cw.category_id = c.category_id
          AND c.category_id = s.category_id
          AND s.sku_id = b.sku_id
          AND cw.is_liansuodian = FALSE
        ORDER BY
          cw.warehouse,
          b.materials_id,
          b.qty DESC
    """
    getQueryData(sql)
    pass


# 七日平均销量
# noinspection SqlDialectInspection
def loadMidWeekMean():
    sql = """
        SELECT
          warehouse, -- 微仓编号
          material_id, -- 原料id
          CAST(avg(sales_data) AS SIGNED) -- 销售量
        FROM psm_sales_data
        WHERE batch >= date_sub(curdate(), INTERVAL 7 DAY) AND batch < curdate()
        GROUP BY warehouse, material_id;
    """
    getQueryData(sql)


# 七日最高销量
# noinspection SqlDialectInspection
def loadMidMaxSale():
    sql = """
        SELECT
          warehouse, -- 微仓编号
          material_id, -- 原料id
          max(sales_data) -- 最高销量
        FROM
          psm_sales_data
        WHERE
          batch >= SUBDATE(CURDATE(), INTERVAL 9 DAY)
          AND batch < CURDATE()
        GROUP BY warehouse, material_id
    """
    getQueryData(sql)
    pass


# 加载原料级别配置
# noinspection SqlDialectInspection
def loadMidLevelConf():
    sql = """
        SELECT
          id,
          type,
          material_id, -- 原料id
          bch2,
          material_shelflife,

          store_condition_code,
          category_id,
          warehouse_id, -- 微仓编号
          warehouse_live,
          benfu_waifu,

          city,
          daqu,
          `value`,
          shelf_life,
          create_by,

          create_date,
          update_by,
          update_date,
          remarks,
          del_flag
        FROM psm_rule_map
        WHERE type = 'yuanliaoJibie' AND del_flag = FALSE
    """
    getQueryData(sql)
    pass


# 手工指定原料级别
def doVcMidLevel():
    # 微仓信息
    vc_dict = {}  # 微仓详情 微仓编号 -> 微仓详情
    for line in open('data/1/vc_info.txt'):
        cols = line.rstrip().split('\t')
        # 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = cols
        if type_str == 'WC':
            vc_dict[vc] = cols
        pass

    # 原料信息
    mid_dict = {}  # mid -> []
    for line in open('data/1/mid_info.txt'):
        cols = line.strip().split('\t')
        # 原料id 原料名称 分类id 温区 分类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
        mid, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = cols
        mid_dict[mid] = cols

    # 外阜标记
    vc_outer_dict = {}
    for line in open('data/1/vc_outer.txt'):
        cols = line.strip().split('\t')
        vc, city, flag = cols
        vc_outer_dict[vc] = flag

    # 原料级别规则
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/mid_level_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule

    # 在售列表
    for line in open('data/1/vc_online_mid.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
        wh, vc, mid, cate, name, trunover, store = cols
        _, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = mid_dict[mid]
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = vc_dict[vc]
        outer = vc_outer_dict[vc]
        bch2 = getStoreBatch(vc, cate, store, sl, sl_hour)  # 拣货批次
        mid_level = getValueFromMapRuleCore('yuanliaoJibie', vc, warehouse_live, outer, city,
                                            wh, mid, sl, store, cate, bch2, RuleMapDict
                                            )[0]
        if mid_level is not None and mid_level != '':
            print('\t'.join([wh, vc, mid, mid_level]))
    pass


# 今日还能销量
def doTodayAbleSale():
    # 日期平均销量
    mean_dict = {}  # vc,mid -> sale
    for line in open('data/1/mid_weekmean.txt'):
        cols = line.strip().split('\t')
        vc, mid, sale = cols
        key = ','.join([vc, mid])
        mean_dict[key] = int(sale)
        pass

    # 今日销量
    today_dict = {}  # vc,mid - > sale
    for line in open('data/1/today_sale.txt'):
        cols = line.strip().split('\t')
        vc, mid, sale = cols
        key = ','.join([vc, mid])
        today_dict[key] = int(sale)
    pass

    for k, v in today_dict.iteritems():
        if k in mean_dict:
            able_sale = mean_dict[k] - v
            key = k.replace(',', '\t')
            # 微仓 原料id 还能销量
            print('\t'.join([key, str(v)]))
        pass


# 品类系数
# noinspection SqlDialectInspection
def loadCateParamConf():
    sql = """
        SELECT
          id,
          type,
          material_id, -- 原料id
          bch2,
          material_shelflife,

          store_condition_code,
          category_id,
          warehouse_id, -- 微仓编号
          warehouse_live,
          benfu_waifu,

          city,
          daqu,
          `value`,
          shelf_life,
          create_by,

          create_date,
          update_by,
          update_date,
          remarks,
          del_flag
        FROM psm_rule_map
        WHERE type = 'buhuoPinleiXishu' AND del_flag = FALSE
    """
    getQueryData(sql)
    pass


# 手工指定品类系数
def doCateParam():
    # 微仓信息
    vc_dict = {}  # 微仓详情 微仓编号 -> 微仓详情
    for line in open('data/1/vc_info.txt'):
        cols = line.rstrip().split('\t')
        # 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = cols
        if type_str == 'WC':
            vc_dict[vc] = cols
        pass

    # 原料信息
    mid_dict = {}  # mid -> []
    for line in open('data/1/mid_info.txt'):
        cols = line.strip().split('\t')
        # 原料id 原料名称 分类id 温区 分类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
        mid, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = cols
        mid_dict[mid] = cols

    # 外阜标记
    vc_outer_dict = {}
    for line in open('data/1/vc_outer.txt'):
        cols = line.strip().split('\t')
        vc, city, flag = cols
        vc_outer_dict[vc] = flag

    # 品类系数规则
    RuleMapDict = {}  # 规则字典 key ->
    for line in open('data/1/cate_param_conf.txt'):
        cols = line.rstrip().split('\t')
        rule = RuleMapDto.init(cols)
        key = rule.getKey()
        RuleMapDict[key] = rule

    # 在售列表
    for line in open('data/1/vc_online_mid.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
        wh, vc, mid, cate, name, trunover, store = cols
        _, mid_name, cateid, store, cate_name, sl, unit, remark, is_short_life, is_scanting, sl_hour = mid_dict[mid]
        vc, name, warehouse_live, type_str, is_lian_suo_dian, province, city = vc_dict[vc]
        outer = vc_outer_dict[vc]
        bch2 = getStoreBatch(vc, cate, store, sl, sl_hour)  # 拣货批次
        cate_param = getValueFromMapRuleCore('buhuoPinleiXishu', vc, warehouse_live, outer, city,
                                             wh, mid, sl, store, cate, bch2, RuleMapDict
                                             )[0]
        if cate_param is not None and cate_param != '':
            print('\t'.join([wh, vc, mid, cate_param]))
    pass


# 计算应补数量
def doShouldSupply():
    # 应补数量 = 应有库存 -库存
    vc_inv_dict = {}  # 微仓编号_原料 -> 微仓库存
    # 读取批次与库存
    for line in open('data/2/vc_mid_inv.txt'):
        cols = line.split('\t')
        vc, mid, inv = cols
        key = ','.join([vc, mid])  # 微仓编号,原料id
        vc_inv_dict[key] = int(inv)  # 现有库存
        pass

    # 今日还能销售
    able_dict = {}  # vc,mid -> 销量
    for line in open('data/1/today_ablesale.txt'):
        cols = line.strip().split('\t')
        vc, mid, value = cols
        key = ','.join([vc, mid])
        able_dict[key] = int(value)
        pass

    # 原料最小规格
    unit_dict = {}  # wh,mid -> value
    for line in open('data/1/mid_unit.txt'):
        cols = line.strip().split('\t')
        wh, mid, value = cols
        key = ','.join([wh, mid])
        unit_dict[key] = int(value)
        pass

    # 从大数据部读取应有有数量
    algo_shouldbe_dict = {}  # vc,mid ->value
    for line in open('data/1/algo_shouldbe.txt'):
        cols = line.strip().split('\t')
        # 微仓编号 原料id 应有库存
        vc, mid, yy = cols
        key = ','.join([vc, mid])
        algo_shouldbe_dict[key] = int(yy)

    # 黑名单
    black_set = set()  # vc,mid -> flag
    for line in open('data/1/black_mid.txt'):
        cols = line.strip().split('\t')
        wh, vc, mid, flag = cols
        key = ','.join([vc, mid])
        black_set.add(key)

    # 遍历在线列表
    for line in open('data/1/vc_online_mid.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
        wh, vc, mid, cate, name, trunover, store = cols
        key = ','.join([vc, mid])

        # 过滤黑名单
        if key in black_set:
            continue

        # 从大数据部获取应有数量
        if key in algo_shouldbe_dict:
            # 应补 = 应有 - 现有库存 + 今日还能
            shouldbe = algo_shouldbe_dict[key]  # 应有
            inv = vc_inv_dict.get(key, 0)  # 现有库存
            able = able_dict.get(key, 0)  # 今日还能
            should_supply = shouldbe - inv + able  # 应补数量

            unit = unit_dict.get(key, 1)
            should_supply = int(should_supply / unit) * unit + unit

            # 大仓编码 微仓编号 原料id 应有 应补数量
            ls = [wh, vc, mid, algo_shouldbe_dict[key], should_supply]
            print('\t'.join(map(str, ls)))
        else:
            logger.error('%s 没查到应有' % key)
        pass

    pass


# 过滤最大补货数量
def filterMaxSupply():
    # 最大补货数量
    max_supply_dict = {}  # vc,mid -> value
    for line in open('data/1/vc_mid_max_supply.txt'):
        cols = line.strip().split('\t')
        wh, vc, mid, value = cols
        key = ','.join([vc, mid])
        max_supply_dict[key] = int(value)

    # 应补数量
    for line in open('data/1/vc_mid_max_supply.txt'):
        cols = line.strip().split('\t')
        wh, vc, mid, value = cols
        supply = int(value)  # 应补数量

        key = ','.join([vc, mid])
        if key in max_supply_dict:
            max_supply = max_supply_dict[key]
            supply = min(supply, max_supply)  # 取上线
        else:
            pass

        ls = [wh, vc, mid, supply]
        print('\t'.join(map(str, ls)))
    pass


# 周转天数 @todo 能量算法

# 分配
def allocation():
    # 分配
    # 大仓库存
    wh_inv_dict = {}  # wh,mid -> inv
    for line in open('data/2/wh_mid_inv.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 原料id 大仓库存
        wh, mid, inv = cols
        key = ','.join([wh, mid])
        wh_inv_dict[key] = int(inv)

    # 现有库存
    vc_inv_dict = {}  # wh,mid -> inv
    for line in open('data/2/vc_mid_inv.txt'):
        cols = line.strip().split('\t')
        # 大仓编码 原料id 大仓库存
        vc, mid, inv = cols
        key = ','.join([vc, mid])
        vc_inv_dict[key] = int(inv)

    # 规格
    for line in open('data/1/mid_unit.txt'):
        pass
    # 大规格

    # 应补数量
    vc_inv_dict = {}  # wh,mid -> inv
    for line in open('data/1/fileter_maxsupply_should_supply.txt'):
        cols = line.strip().split('\t')
        # 微仓编码 原料id 应有 应补
        vc, mid, shoulbe, supply = cols
        key = ','.join([wh, mid])
        vc_inv_dict[key] = int(inv)
        # todo print
        print

    pass


def isTomrrowPlayDay():
    """
    明天是否为休息日
    :return:
    """
    flag = False
    tomrrow = datetime.now() + timedelta(days=1)
    if tomrrow.weekday() in {0, 6}:
        flag = True
    return flag


def test():
    logger.info('test')
    pass


# 主要流程
def main():
    # 初始化补货参数
    # (1) 明日是否需要补货 data/1/stop_shop.txt : 日期 休
    # (2) 原料等级 data/1/mid_level.txt : 大仓编码 原料id 等级
    # (3) 原料售卖天数（15天内） data/1/sale_day.txt : 大仓编码 原料ID 第一次售卖距今天数
    # (4) 今日已补数量 data/1/already_supply.txt : 微仓编码 原料ID 已补数量
    # (5) 所有辅料 data/1/sub_mid.txt : 商品sku 原料id
    # (6) 微仓两天内订单量 data/1/vc_order.txt ：微仓编号 订单量
    # (7) 获取一周内的微仓品类销量 data/1/vc_cate_order.txt : 微仓编号 品类 订单量
    # (8) 站点等级 data/1/vc_level.txt : 微仓编号 等级
    # (9) 新品&促销品 data/1/new_promo.txt ：大仓编码 城市 原料id 品类 原料名称 周转天数 温区 is_main rebate total_qty
    # (10) 干仓预留 data/1/reserve_inv.txt : 大仓编码 原料id 干仓预留库存
    # (11) 明天是否为休息日(周六、周日) isTomrrowPlayDay()
    # (12) 算法小组计算的应有数量 data/1/algo_shouldbe.txt : 微仓编码 原料id 应有库存

    # 基础数据
    # (1) 微仓详情 data/1/vc_info.txt : 仓库编码 仓库名称 warehouse_live 仓库类型 连锁店 省 城市
    # (2) 原料详情 data/1/mid_info.txt : 原料id 原料名称 品类id 存储温区 一级品类名称 保质期 单位 标记 是否短保 是否标品 保质期小时

    # 业务数据
    # (1) 待补货微仓(前两天有销量的微仓) 基础补货外围循环数据 data/1/active_vc.txt : 微仓编码 城市 微仓名称
    # (2) 外阜/(本阜+外阜) 比例 data/1/wh_outer_ratio.txt : 大仓编码 外阜比例
    # (3) 外阜/(本阜+外阜) 品类比例 data/1/wh_outer_cate_ratio.txt : 大仓编码 原料id 外阜比例

    # 应补微仓计算数据
    # (1) 微仓外阜标记 data/1/vc_outer.txt : 微仓编码 外阜标记
    # (2) 微仓批次 data/1/vc_batch.txt : 微仓编号 批次时间
    # (3) 在售清单 data/1/online_mid.txt : 大仓编码 原料id 品类 原料名称 周转天数 温区
    # (4) 追加新品促销品后的在售列表 data/1/vc_online_mid.txt : # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区

    # (5) 大仓系数 data/1/wh_param.txt : 大仓编码 系数
    # (6) 微仓系数 data/1/vc_param.txt : 微仓编码 系数
    # (7) 总系数 = 大仓系数 * 微仓系数 , 默认系数=1.0

    # (8) 微仓七日平均  data/1/vc_week_sale.txt : 微仓编号 平均销量
    # (9) 微仓明日星期X平均单量 data/1/vc_tommorow_week_sale.txt : 微仓编号 单量
    # (10) 微仓明日占比 = 星期X平均单量/七日平均 data/1/vc_tomorrow_ratio.txt : 微仓编号 占比

    # 应补单品计算数据,遍历在售列表,单品处理
    # (1) 黑名单(不补货) data/1/black_mid.txt : 大仓编码 微仓编码 原料id 标记
    # (2) 辅料(单独补货) data/1/sub_mid.txt : 商品sku 原料id
    # (3) 大仓库存(大仓无货不补货) data/2/wh_mid_inv.txt : 大仓编码 原料id 库存数量
    # (4) 微仓品类明日占比 = 4个星期x的平均单量/4个星期的平均单量 data/1/vc_cate_tomorrow_tatio.txt : 微仓编码 品类 比例
    # (5) 大规格 data/1/vc_mid_big_unit.txt ：大仓编码 微仓编码 原料id 大规格

    # (6) 微仓现有库存 data/2/vc_mid_inv.txt : 微仓编码 原料id 现有库存
    # (7) 大仓现有库存 data/2/wh_mid_inv.txt : 大仓编码 原料id 大仓库存

    # (8) 今日销量 data/1/today_sale.txt : 微仓编码 原料id 销量
    # (9) 最大补货数量 data/1/vc_mid_max_supply.txt : 大仓编码 微仓编码 原料id 最大补货量

    # (10) 原料规格(默认规格:1) data/1/mid_unit.txt ：大仓编码 原料id 规格

    # (11) 原料周转天数 data/1/mid_turnover.txt : 原料ID 周转天数
    # (12) 原料配置周转天数 data/1/mid_turnover_rule.txt : 大仓编码 微仓编码 原料id 周转天数
    # (13) 配置周转天数优先，次之原料周转天数，默认周转天数为1.0

    # (14) 新品促销品 a.按原料、大仓获取数量 b.按原料、大仓、城市获取数量 c.微仓7日品类销量 data/1/vc_cate_order.txt
    # (15) 今日还能销售 = 七日平均 - 今日销量
    #  *  data/1/mid_weekmean.txt 七日平均销量 : 微仓编码 原料id 销量
    #  *  data/1/today_sale.txt 今日销量 : 微仓编号 原料id 销量
    #  *  data/1/today_ablesale.txt 今日还能销量 : 微仓编号 原料id 还能销售
    #  今日还能销量
    # ?? 7日平均 A级原料取七日平均理论销量,轻食&蔬菜小于8天取七日平均理论销量,小于4天取七日平均理论销量 其他取七日平均真是销量
    #      销售天数大于10且品类FREEZE取14天, getNdayMeanSales()七日平均销量
    # (16) 七日最高销量 data/1/mid_maxsale.txt ：微仓编码 原料id 最高销量
    # (17) 手动原料级别 data/1/vc_mid_level.txt :  微仓编号 原料ID 级别(A、B、C)
    # (18) 品类系数 data/1/cate_param.txt : 大仓编码 微仓编码 原料id 品类系数
    # (19) 总系数 = 品类系数 * 原料系数

    # 应补数量计算
    # (1)


    # (1)平均分配库存
    # 读取补货单

    # (2)过滤库容

    # (3)生成补货单、扣APT库存

    # (4)发送辅料信息

    # (5)保存日志

    # (6)同步ATP
    pass


if __name__ == '__main__':
    fire.Fire()
