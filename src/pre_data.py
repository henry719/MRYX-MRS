#!/usr/bin/env python
# -*- coding:utf-8 -*- 
"""
一个python文件
"""
import sys

reload(sys)
sys.setdefaultencoding('utf-8')
import os

from pyspark import SparkConf, SparkContext, HiveContext
from lib import rule_name_list, interior_warehouse_list, fridge_warehouse_list, get_other_day, dp_delt
from conf import run_day, day_span, hive_database

__author__ = 'dongsibei'


# 获取促销信息
def get_promo_info(items):
    vc, cid, mid = items

    wh = vc.split('-')[0]  # 大仓编号

    promo_dict = promo_info.value  # 促销清单
    promo_ls = []  # 促销系数列表

    key = vc + '_' + mid
    promo_ls.append(promo_dict.get(key, None))

    key = vc + '_' + cid
    promo_ls.append(promo_dict.get(key, None))

    key = wh + '_' + mid
    promo_ls.append(promo_dict.get(key, None))

    key = wh + '_' + cid
    promo_ls.append(promo_dict.get(key, None))

    promo = 0.0
    for v in promo_ls:
        if v is not None:
            promo, mark, prior = v
            break
        pass
    return promo


# 获取批次时间
def get_transport_time(items):
    # 微仓编码 分类 原料id 温区 保质期(天) 城市 促销系数 #销量#理论销量#促销#日期###销量#理论销量#促销#日期
    vc, cid, mid, store, sl, city, sr, promo = items

    wh = vc.split('-')[0]  # 大仓编号
    if wh == 'MRYXBJN' or wh == 'MRYXSZ':
        is_interior = None
    elif vc in interior_warehouse_list:
        is_interior = None
    else:
        is_interior = 'WF'

    condition_list = [vc, is_interior, None, wh, mid, None, store, cid]
    candidate_list = [[transport_info.value, ], ['', ]]
    res = -1
    for i in range(len(condition_list)):
        new_candidate_list = [[], []]
        for j in range(len(candidate_list[0])):
            sub_list = candidate_list[0][j]
            if rule_name_list[i] in sub_list:
                new_candidate_list[0].append(sub_list[rule_name_list[i]])
                new_candidate_list[1].append(candidate_list[1][j] + 'None_')
            if condition_list[i] is not None:
                if condition_list[i] in sub_list:
                    new_candidate_list[0].append(sub_list[condition_list[i]])
                    new_candidate_list[1].append(candidate_list[1][j] + condition_list[i] + '_')
        candidate_list = new_candidate_list
    score = -1
    for i in range(len(candidate_list[1])):
        hit_list = candidate_list[1][i].split('_')
        tmp_score = 0
        for j in range(len(hit_list) - 1):
            if hit_list[j] != 'None':
                tmp_score += 1
            tmp_score *= 2
        if score < tmp_score:
            score = tmp_score
            res = candidate_list[0][i]
    return res


# 获取促销信息
def get_promo(spark, last_day):
    dp, _ = get_other_day(last_day, 0)
    promos = spark.sql(
        '''
          SELECT
            concat(concat(vc,'_'), mid),
            CASE WHEN promo IS NULL
              THEN 0.0
              ELSE promo
            END promo,
            mark, id
          FROM dw.promotion_info
          WHERE dp='%s'
        ''' % dp
    ).map(tuple).collect()

    promo_info = {}  # 促销系数字典 微仓_原料id -> [促销系数-1,标记,优先级]
    # 微仓_原料id 促销系数 标记(微仓/城市) prior(优先级)
    for key, promo, mark, prior in promos:
        if key not in promo_info:
            promo_info[key] = [promo - 1, mark, prior]
        else:
            last_mark = promo_info[key][1]
            last_prior = promo_info[key][2]
            # 促销颗粒度 mark大的表示微仓级别，mark小的表示城市级别
            if mark > last_mark:  # vc > city
                promo_info[key] = [promo - 1, mark, prior]
            elif mark == last_mark:
                if prior > last_prior:  # later > prior 促销优先级
                    promo_info[key] = [promo - 1, mark, prior]
            pass
    return promo_info


# 获取批次信息
def schedule_fetch(spark):
    schedule = spark.sql(
        '''
              SELECT
                material_id,bch2,store_contition_code,
                category_id,warehouse_id,is_interior,
                city,district,shelf_life,
                transport_time
              FROM dw.transport_rules
        '''
    ).map(tuple).collect()

    transport_info = {}  # 批次时间字典 条件1,条件2... ->批次时间
    for poll in schedule:
        material_id = poll[0] if poll[0] != '' else None
        store_condition = 'ROOM' if (poll[1] is not None and poll[1] != '') else (poll[2] if poll[2] != '' else None)
        category_id = poll[3] if poll[3] != '' else None
        warehouse_id = poll[4] if poll[4] != '' else None
        is_interior = poll[5] if poll[5] != '' else None
        city = poll[6] if poll[6] != '' else None
        district = poll[7] if poll[7] != '' else None
        shelf_life = poll[8] if (poll[8] != '' and poll[8] is not None) else None
        transport_time = min(max(21 - int(poll[9]), 0), 12) / 12.0 if poll[9] is not None else 1.0

        if warehouse_id is None:
            if 'ALL_WAREHOUSE' not in transport_info:
                transport_info['ALL_WAREHOUSE'] = {}
            warehouse_sub = transport_info['ALL_WAREHOUSE']
        else:

            if warehouse_id not in transport_info:
                transport_info[warehouse_id] = {}
            warehouse_sub = transport_info[warehouse_id]

        if is_interior is None:
            if 'ALL_INTERIOR' not in warehouse_sub:
                warehouse_sub['ALL_INTERIOR'] = {}
            interior_sub = warehouse_sub['ALL_INTERIOR']
        else:
            if is_interior not in warehouse_sub:
                warehouse_sub[is_interior] = {}
            interior_sub = warehouse_sub[is_interior]

        if city is None:
            if 'ALL_CITY' not in interior_sub:
                interior_sub['ALL_CITY'] = {}
            city_sub = interior_sub['ALL_CITY']
        else:
            if city not in interior_sub:
                interior_sub[city] = {}
            city_sub = interior_sub[city]

        if district is None:
            if 'ALL_DISTRICT' not in city_sub:
                city_sub['ALL_DISTRICT'] = {}
            district_sub = city_sub['ALL_DISTRICT']
        else:
            if district not in city_sub:
                city_sub[district] = {}
            district_sub = city_sub[district]

        if material_id is None:
            if 'ALL_MATERIAL' not in district_sub:
                district_sub['ALL_MATERIAL'] = {}
            material_sub = district_sub['ALL_MATERIAL']
        else:
            if material_id not in district_sub:
                district_sub[material_id] = {}
            material_sub = district_sub[material_id]

        if shelf_life is None:
            if 'ALL_SHELF_LIFE' not in material_sub:
                material_sub['ALL_SHELF_LIFE'] = {}
            life_sub = material_sub['ALL_SHELF_LIFE']
        else:
            if shelf_life not in material_sub:
                material_sub[shelf_life] = {}
            life_sub = material_sub[shelf_life]

        if store_condition is None:
            if 'ALL_CONDITION' not in life_sub:
                life_sub['ALL_CONDITION'] = {}
            condition_sub = life_sub['ALL_CONDITION']
        else:
            if store_condition not in life_sub:
                life_sub[store_condition] = {}
            condition_sub = life_sub[store_condition]

        if category_id is None:
            if 'ALL_CATEGORY' not in condition_sub:
                condition_sub['ALL_CATEGORY'] = transport_time
            else:
                print 'duplicate all condition error.'
        else:
            if category_id not in condition_sub:
                condition_sub[category_id] = transport_time
            else:
                if transport_time != condition_sub[category_id]:
                    print 'duplicate condition error.'
        pass
    return transport_info


# 处理原料数据
def get_data(spark, duration, database):
    # 原始销量数据 (vc,cid,mid,sl,sr,dp)
    mts = spark.sql(
        """
          SELECT
            vc,cid,mid,
            store,sl,city,
            sr
          FROM {database}.wh_vc_ts
        """.format(database=database)
    ).rdd.map(
        # vc,cid,mid, store,sl,city, sr,promo
        lambda x: list(x) + [get_promo_info(x[:3])]  # 拼接促销数据
    ).map(
        # vc,cid,mid, store,sl,city, sr,promo,transport_time
        lambda x: list(x) + [get_transport_time(x)]  # 拼接发单批次
    ).map(
        lambda x: ((x[0], x[1]), x[:])  # 微仓_品类
    )

    # 销量数据在内存持久化
    cts = spark.sql(
        """
          SELECT vc,cid,sr
          FROM {database}.wh_vc_category_ts
        """.format(database=database)
    ).map(
        lambda x: ((x[0], x[1]), x[2])  # 微仓_品类
    )

    # 拼接品类信息
    mts = mts.leftOuterJoin(cts).map(
        # vc,cid,mid, store,sl,city, sr,promo,transport_time,cts
        lambda x: list(x[1][0]) + [x[1][1]]
    )

    mts.repartition(400).toDF(
        ['vc', 'cid', 'mid', 'store', 'sl', 'city', 'sr', 'promo', 'transport_time', 'cts']
    ).registerTempTable('result')  # 注册临时表
    spark.sql(
        '''
            drop table if exists {database}.mts
        '''.format(database=database)
    )
    spark.sql(
        '''
            create table {database}.mts as
              select * from result
        '''.format(database=database)
    )


if __name__ == '__main__':
    os.environ['SPARK_HOME'] = '/data/src/spark'
    sparkConf = SparkConf().setSparkHome(
        '/data/src/spark'
    ).setAppName(
        'pre_data'
    ).set(
        'spark.ui.port', 4099
    )

    sc = SparkContext(conf=sparkConf)
    sc.addFile('lib.py')
    sc.addFile('conf.py')

    hc = HiveContext(sc)
    last = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    duration = day_span
    last_day = run_day
    database = hive_database  # 数据保存位置

    # 促销信息
    global promo_info
    promo = get_promo(hc, last_day)
    promo_info = sc.broadcast(promo)  # 广播促销信息

    # 批次信息
    global transport_info
    transport_time_info = schedule_fetch(hc)
    transport_info = sc.broadcast(transport_time_info)  # 广播批次信息

    get_data(hc, duration, database)
