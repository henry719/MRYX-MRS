#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 16 17:09:00 2018

@author: wayaya
"""
import os

from pyspark import SparkConf, SparkContext
from pyspark.sql import HiveContext

from lib import dpptime, get_other_day, dp_delt, interior_warehouse_list, fridge_warehouse_list
from lib import strpSeries, outlier_box
from conf import run_day, day_span, yy_database
from pandas import Series, DataFrame
import numpy as np
import datetime
import sys
import math
from sklearn.linear_model import LinearRegression

reload(sys)
# noinspection PyUnresolvedReferences
sys.setdefaultencoding('utf-8')

fridge_index = 0.9  # 冰箱仓补货系数
fridge_material_sl = {

}


# ': 1,(dp,vc,cid,sr)=> ((vc,cid),'sr##dp')
def tran0(row):
    vc, cid, mid, store, sl, city, transport_time, promo, mts, cts = row
    vc = str(row[0])
    wh = vc.split('-')[0]
    cid = row[1]
    ts = str(row[-1]).split('##')

    # 过滤重大促销日
    ts = filter(
        lambda x: x.split('#')[-1] not in {
            '20180517', '20180518', '20180519', '20180520',
            '20180616', '20180617', '20180618'
        }, ts
    )
    if wh in {'MRYXSHW', 'MRYXNJ'}:
        ts = filter(lambda x: x.split('#')[-1] not in {'20180521'}, ts)

    cts = '##'.join(list(map(lambda x: '#'.join(x.split('#')[1:]), ts)))
    return (vc, cid), (vc, cid, mid, store, sl, city, transport_time, promo, mts, cts)


def tran1(row, begin, end, last_day):
    # 微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(Series('日期','理论销量'))
    vc, cid, mid, store, sl, city, transport_time, promo, mts, cts = row
    vc = str(row[0])
    wh = vc.split('-')[0]
    cid = row[1]
    mid = str(row[2])
    store = str(row[3])
    sl = int(row[4])
    sl = 1 if sl <= 0 else sl
    city = str(row[5])
    ts = str(row[-2]).split('##')

    if wh in {'MRYXBJN', 'MRYXTJ', 'MRYXTJW', 'MRYXSHW', 'MRYXSHD'}:
        begin, _ = get_other_day(last_day, -14)

    # 取历史28天之内的数据
    mts = list(filter(lambda x: end >= x.split('#')[-1] >= begin, ts))
    mts = list(map(lambda x: '#'.join(x.split('#')[1:]), mts))  # 删除真实销量

    if len(mts):
        dty = mts[len(mts) - 1].split('#')[-1]  # 获取最后一天的日期
        dtdif = list()

        # 计算数据间相差的天数
        for j in np.arange(len(mts)):
            if j == len(mts) - 1:
                dty = mts[j].split('#')[-1]
                # dtdif.append(dpdiff(get_n_dp(0), dty))
                dtdif.append(dp_delt(last_day, dty))  # 距离计算日的天数
            else:
                dty = mts[j].split('#')[-1]
                dtn = mts[j + 1].split('#')[-1]
                # dtdif.append(dpdiff(dtn, dty))
                dtdif.append(dp_delt(dtn, dty))  # 距离下一条数据的天数

        bk_point = 0  # 断点
        dtdiff_addzeros = list()
        str_len = len(dtdif) - 1

        # 取出日期差>=14天的断点和日期差>=2天和<14天的下标 @todo 有待优化用14截断是否合理
        for i in np.arange(str_len + 1):
            if dtdif[str_len - i] >= 14:
                bk_point = str_len - i
                break
            elif 14 > dtdif[str_len - i] >= 2:
                dtdiff_addzeros.append(str_len - i)

        if bk_point == str_len:
            # mts返回null
            mts = []
        elif bk_point == 0:
            # 补零操作
            if len(dtdiff_addzeros):
                for n in np.arange(len(dtdiff_addzeros)):
                    add_index = dtdif[dtdiff_addzeros[n]]
                    curday = mts[dtdiff_addzeros[n]].split('#')[-1]
                    for k in np.arange(add_index - 1):
                        mts_add_temp = ['0', '1']
                        curday = (dpptime(curday) + datetime.timedelta(days=1)).strftime("%Y%m%d")
                        mts_add_temp.append(curday)
                        mts.insert(dtdiff_addzeros[n] + 1 + k, ('#'.join(mts_add_temp)))
        else:
            # 先将mts进行截断
            mts = mts[(bk_point + 1):]
            dtdif = dtdif[(bk_point + 1):]
            # dtdiff_addzeros = dtdiff_addzeros - (bk_point + 1)
            dtdiff_addzeros = map(lambda x: x - bk_point - 1, dtdiff_addzeros)

            # 补零操作
            if len(dtdiff_addzeros):
                for n in np.arange(len(dtdiff_addzeros)):
                    add_index = dtdif[dtdiff_addzeros[n]]
                    curday = mts[dtdiff_addzeros[n]].split('#')[-1]
                    for k in np.arange(add_index - 1):
                        mts_add_temp = ['0', '1']
                        curday = (dpptime(curday) + datetime.timedelta(days=1)).strftime("%Y%m%d")
                        mts_add_temp.append(curday)
                        mts.insert(dtdiff_addzeros[n] + 1 + k, ('#'.join(mts_add_temp)))

    # mts = '##'.join(mts)

    #  replace data of promotion day by historic data of the same weekdays.
    # [[促销系数,20180501],[促销系数,20180502]...]
    mts_list = map(lambda x: x.split('#'), mts)

    # print 'mts_list here:', mts_list
    no_promo = {}  # 理论销量
    promo_index = []  # 促销系数索引

    # 促销系数
    for i in range(len(mts)):
        splited = mts_list[i]
        if len(splited) > 2 and float(splited[1]) != 1:
            promo_index.append(i)
        else:
            no_promo[datetime.datetime.strptime(splited[-1], '%Y%m%d')] = float(splited[0])
    if len(no_promo) == 0:
        return
    # 对于有促销的日子，应当重新计算其理论销量
    earliest_date = datetime.datetime.strptime(mts_list[0][-1], '%Y%m%d')  # 第一天的数据日期
    last_date = datetime.datetime.strptime(mts_list[-1][-1], '%Y%m%d')  # 最后一天的数据日期
    for i in range(len(promo_index)):
        promo_data = mts_list[promo_index[i]]
        promo_date = datetime.datetime.strptime(promo_data[-1], '%Y%m%d')
        week_day_date = promo_date - datetime.timedelta(days=7)
        avg_tsr = 0
        count = 0
        while week_day_date >= earliest_date:
            if week_day_date in no_promo:
                avg_tsr += no_promo[week_day_date]
                count += 1
            week_day_date -= datetime.timedelta(days=7)
        week_day_date = promo_date + datetime.timedelta(days=7)
        while week_day_date <= last_date:
            if week_day_date in no_promo:
                avg_tsr += no_promo[week_day_date]
                count += 1
            week_day_date += datetime.timedelta(days=7)
        if count != 0:
            mts_list[promo_index[i]][0] = avg_tsr / count
        else:
            tmp = 0
            for poll in no_promo:
                tmp += no_promo[poll]
            mts_list[promo_index[i]][0] = tmp / len(no_promo)

    # 剔除大促日
    mts_list = list(
        filter(
            lambda x: x[-1] not in {
                '20180517', '20180518', '20180519', '20180520',
                '20180616', '20180617', '20180618'
            }, mts_list
        )
    )
    # 剔除华东促销日
    if wh in {'MRYXSHW', 'MRYXNJ'}:
        mts_list = list(filter(
            lambda x: x[-1] not in {'20180521'}, mts_list)
        )

    mts = map(lambda x: '#'.join([str(x[0]), x[-1]]), mts_list)
    mts = '##'.join(mts)
    # (微仓 分类 原料id 温区 保质期 城市名称(拼音)) (微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(理论销量#20180501##理论销量#20180502) 分类销量(Series('日期','理论销量'))
    return (vc, cid, mid, store, sl, city), (vc, cid, mid, store, sl, city, transport_time, promo, mts, cts)


# ((vc,cid),((mid,store,sl,mts),cts)) => (vc,cid,mid,sl,mean,sd,q50,yb,percentile)
def tran_out(x, predict_day):
    vc, cid, mid, store, sl, city, transport_time, promo, mts, cts = x
    wh = vc.split('-')[0]
    mts = Series(mts)
    alpha = 7.0
    moving_window = 7
    length = len(mts)

    if wh == 'MRYXBJN' or wh == 'MRYXSZ':
        is_interior = None
    elif vc in interior_warehouse_list:
        is_interior = None
    else:
        is_interior = 'WF'

    slope = 0
    coe_lower = -0.2
    coe_upper = 0.2
    if city == 'BEIJING':
        coe_lower = -0.3
        coe_upper = 0.3

    ts_filtered = linear_filter(mts, alpha)
    m_star = 0
    if length >= 7:
        if length > 14 or wh in {'MRYXBJN', 'MRYXTJ', 'MRYXTJW', 'MRYXSHW', 'MRYXNJ', 'MRYXSHD'}:
            sd = 0
            # ts_reversed = ts_filtered.values[-1::-1]
            ts_sma = ts_filtered.rolling(moving_window, 1, center=True, ).mean()
            # ts_sma = pd.Series(data=ts_sma_resversed.values[-1::-1], index=ts_filtered.index)

            y = ts_sma.values
            x = np.arange(length).reshape(-1, 1)
            model = LinearRegression()
            model.fit(x, y)
            slope = model.coef_[0]
            ts_epsilon = ts_filtered - slope * Series(range(length), index=ts_filtered.index)
        else:
            sd = 1
            ts_epsilon = Series(ts_filtered.values, index=ts_filtered.index)

        # coe = get_week_coe(ts_epsilon)
        coe = get_week_coe(cts, coe_lower, coe_upper)
        epsilon_mean = ts_epsilon.mean()
        ts_Y = eliminate_coe(ts_epsilon, coe, epsilon_mean)
        (mul, m_star) = ts_predict(ts_Y, sl)
        yb = 0
        predict_value = []
        predict_index = []
        for i in range(0, int(math.ceil(mul))):
            weekday = (predict_day + datetime.timedelta(days=i)).weekday()
            if weekday not in coe:
                coe_index = 0
            else:
                coe_index = coe[weekday]
            predict_value.append(coe_index * epsilon_mean + m_star)
            predict_index.append(predict_day + datetime.timedelta(days=i))
        for i in range(0, len(predict_value)):
            predict_value[i] += slope * (length + 1)

        for i in range(0, min(min(int(math.ceil(sl - 1)), 5), int(math.ceil(mul)))):
            is_half = 1 if i + 0.5 < mul else 0.5
            one_day_value = predict_value[i] if predict_value[i] > 0 else 0
            yb += one_day_value * is_half
        # print 'yb:', yb
        # if m_star < 1:
        #     m_star = 1.0
        yb += (promo + (1 + promo) * transport_time) * m_star
        mul_a = min(int(math.ceil(sl)), 5)
        mul_b = int(math.ceil(mul))
        mul_real = mul_a if mul_a < mul_b else mul
    else:
        sd = 2
        coe = get_week_coe(cts, coe_lower, coe_upper)
        # print 'coe here: ', coe
        m_star = ts_filtered.mean()
        mul = max(1.0, min(sl - 1, 3.0))
        mul_real = mul
        yb = 0
        # if m_star < 1:
        #     m_star = 1.0
        for i in range(0, int(mul)):
            weekday = (predict_day + datetime.timedelta(days=i)).weekday()
            if weekday in coe:
                yb += (1 + coe[weekday]) * m_star
            else:
                yb += m_star
        yb += (promo + (1 + promo) * transport_time) * m_star

    mean = float(round(mts.mean(), 2))
    # sd = float(round(mts.std(), 2))
    median = float(round(mts.quantile(0.5), 2))
    median = 1 if median < 1 else median
    q95 = float(round(mts.quantile(0.95), 2))
    if (store == 'FREEZE' or store == 'COLD') and vc in fridge_warehouse_list:
        yb = fridge_index * yb
        # print 'fridge station here', store, vc
    yb = math.ceil(yb)
    if yb < 1.0:
        yb = 1.0
    return (vc, cid, mid, store, float(sl), float(mean), float(sd), float(median), float(yb), float(mul_real),
            float(q95), float(promo), str(transport_time), float(m_star))


def eliminate_coe(x, coe, mean):
    value = x.values
    index = x.index
    res_value = []
    for i in range(0, len(index)):
        week_index = coe[index[i].weekday()] if index[i].weekday() in coe else 0.0
        res_value.append(value[i] - mean * week_index)
    return Series(data=res_value, index=index)


def get_week_coe(cts, lower=-0.2, upper=0.2):
    index = cts.index
    value = cts.values
    week = np.array(list(map(lambda x: x.weekday(), index)))
    df = DataFrame({'w': week, 'v': value}, columns=['w', 'v'])
    mean = cts.mean()
    wv = ((df.groupby(['w'])['v'].mean() - mean) / mean).round(10)
    wv = wv.apply(lambda x: min(max(lower, x), upper))
    return wv


def linear_filter(x, alpha=7.0):
    res = [x[0], ]
    ttl_wt = 1
    mv_sum = x[0]
    for index in range(1, len(x)):
        mv_sum += x[index - 1] * index
        ttl_wt += index
        pre_mean = max(mv_sum / ttl_wt, 1.0)
        res.append(min(alpha * pre_mean, x[index]))
    return Series(data=res, index=x.index)


# 序列处理空值与离群值
def solve_na_outlier(x):
    if len(x) == 0:
        return Series()
    series_pri = Series(x)
    series_solve = Series(data=outlier_box(series_pri.values), index=series_pri.index)
    return series_solve


# 根据时序分位数预测
# return: (mean,sd,q50,yb,percentile,n,week)
def ts_predict(x, sl, is_SH=False):
    x_min = x.min()
    x = Series(x) + abs(x_min)
    miu = float(round(x.mean(), 2))
    sigma = float(round(x.std(), 2))
    sigma = 0 if math.isnan(sigma) else sigma
    q50 = float(round(x.quantile(0.5), 2))
    if is_SH:
        q95 = float(round(x.quantile(0.98), 2))
    else:
        q95 = float(round(x.quantile(0.95), 2))
    yb = 0
    mul = 0
    cap_sl = 10.0

    if abs(q50 + sigma) > 0.01:
        m_star = (q50 * q50 + miu * sigma) / (q50 + sigma)
    else:
        m_star = q50

    # print 'm_star + min.x:', m_star
    # if m_star < 1:
    #     m_star = 1.0
    #     mul = 1.0
    if sl == 1:
        mul = 1.0
    elif sl == 2:
        mul = 1.5
    elif sl == 3:
        mul = 2.0
    elif sl > 3:
        cap_sl = sl - 1  # cap1 related to sl
        lower_cap_mul = min(sl / 2.0, 3.0)
        upper_cap_mul = min(float(cap_sl), 5.0)
        try_mul = lower_cap_mul
        while try_mul <= upper_cap_mul:
            if q95 <= try_mul * m_star:
                mul = try_mul
                break
            else:
                mul = try_mul
                try_mul += 0.5
    mul = mul
    res = (mul, m_star - abs(x_min))
    return res


# noinspection SqlDialectInspection
def write(spark, dp):
    # mysql -h 10.10.75.56 -u bi_user -pcongku_#2018
    url = 'jdbc:mysql://10.10.75.56:3306/dws?useUnicode=true&characterEncoding=utf-8&useSSL=false'
    table = 'wh_material_info'
    prop = {'user': 'bi_user', 'password': 'congku_#2018', 'driver': 'com.mysql.jdbc.Driver'}
    spark.sql("""
               select wh, vc, cid, mid,median, yb, dp
                 from da.wh_material_info where dp='%s'
               """ % dp
              ).write.jdbc(url, table, 'overwrite', prop)


def series_tostr(x):
    d = x.to_dict()
    out_ls = []
    for k, v in sorted(d.iteritems(), key=lambda x: x[0]):
        ls = [v, str(k).split(' ')[0].replace('-', '')]
        out_ls.append('#'.join(map(str, ls)))
    return '##'.join(out_ls)


# noinspection SqlDialectInspection
def get_inventory(spark):
    """
    返回库存
    :param spark: hiveContext
    :return: 大仓库存RDD，微仓库存RDD
    """
    # 大仓逻辑库存
    # 大仓编码 原料编码 逻辑库存
    wh_inventory = spark.sql('''
        SELECT wh, mid, inv
        FROM supply.wh_mid_inv
    ''').rdd.map(tuple).repartition(1)
    wh_inventory.persist()

    # 微仓逻辑库存
    # 微仓编码 原料id 逻辑库存
    vc_inventory = spark.sql('''
        SELECT vc, mid, inv
        FROM supply.vc_mid_inv
    ''').rdd.map(tuple).repartition(1)
    vc_inventory.persist()

    return wh_inventory, vc_inventory


def get_data(spark, duration, last_day, database):
    """
    微仓原料应有数量预测
    :param spark: 上下文
    :param duration: 数据天数
    :param last_day: 计算日期
    :param database: 预测的应有库存保存的位置
    :return: 原料数据 预测结果
    """
    dp, _ = get_other_day(last_day, 0)
    print 'date: ', dp
    print 'database:', database
    begin, _ = get_other_day(last_day, -duration)  # 数据起始日期
    end = get_other_day(last_day, -1)  # 数据截止日期

    last_date = datetime.datetime.strptime(last_day, '%Y%m%d')
    predict_date = (last_date + datetime.timedelta(days=1)).date()  # 预测下一天

    # noinspection SqlDialectInspection
    mts = spark.sql(
        # 微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数
        # 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(实际销量#理论销量#20180501##实际销量#理论销量#20180502)
        """
         SELECT vc,cid,mid,store,sl,city,transport_time,promo,
                sr,cts
         FROM {database}.mts
        """.format(database=database)
    ).map(tuple).filter(
        # 过滤原料销量: 原料销量序列的最后一天 距离last_day的天数小于7 且 数据序列长度大于=1
        # 输入: 微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(实际销量#理论销量#20180501##实际销量#理论销量#20180502)
        # 输出: 微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(实际销量#理论销量#20180501##实际销量#理论销量#20180502)
        lambda x: abs(
            dp_delt(x[-2].split('##')[-1].split('#')[-1], last_day)
        ) <= 7 and len(x[-2].split('##')) >= 1
    )
    mts.persist()  # 销量数据在内存持久化
    mts_origin = mts  # 用于返回计算应补数量

    # 处理 分类数据
    mts = mts.map(
        # 处理分类数据: 删除 分类实际销量
        # 输入: 微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(实际销量#理论销量#20180501##实际销量#理论销量#20180502)
        # 输出: (微仓编码,原料id) (微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(理论销量#20180501##理论销量#20180502))
        tran0
    ).map(
        # 处理分类数据: 分类理论销量数据 转化为 pandas.Series
        # 输入: (微仓编码,原料id) (微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(理论销量#20180501##理论销量#20180502))
        # 输出: (微仓编码,原料id) [微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#20180501##实际销量#理论销量#20180502) 分类销量(Series('日期','理论销量'))]
        lambda x: (x[0], list(x[1][:-1]) + [strpSeries(x[1][-1])])
    ).map(
        # 处理分类数据: 分类理论销量 处理空值与离群值 取值控制在[q05 与 q95]之间
        # 输入: (微仓编码,原料id) [微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(Series('日期','理论销量'))]
        # 输出：(微仓编码,原料id) [微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(Series('日期','理论销量'))]
        lambda x: (x[0], list(x[1][:-1]) + [solve_na_outlier(x[1][-1])])
    ).map(
        # 处理原料数据: 截取28天的数据 对缺失数据进行补充 处理促销系数
        # 输入: (微仓编码,原料id) [微仓编码 分类 原料id 温区 保质期 城市名称(拼音) 批次 促销系数 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502) 分类销量(Series('日期','理论销量'))]
        # 输出: (微仓 分类 原料id 温区 保质期 城市名称(拼音)) (微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(理论销量#20180501##理论销量#20180502) 分类销量(Series('日期','理论销量'))
        lambda x: tran1(x[1], begin, end, last_day)
    ).filter(
        # 处理原料数据: 过滤空值 过滤数据长度为0的
        # 输入: (微仓 分类 原料id 温区 保质期 城市名称(拼音)) (微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(理论销量#20180501##理论销量#20180502) 分类销量(Series('日期','理论销量'))
        # 输出: (微仓 分类 原料id 温区 保质期 城市名称(拼音)) (微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(理论销量#20180501##理论销量#20180502) 分类销量(Series('日期','理论销量'))
        lambda x: x is not None and len(x[1][-2]) > 0
    ).map(
        # 处理原料数据: 原料理论销量 转化为 pandas.Series
        # 输入: (微仓 分类 原料id 温区 保质期 城市名称(拼音)) (微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(理论销量#20180501##理论销量#20180502) 分类销量(Series('日期','理论销量'))
        # 输出: (微仓 分类 原料id 温区 保质期 城市名称(拼音)) [微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(Series('日期','理论销量') 分类销量(Series('日期','理论销量')]
        lambda x: (x[0], list(x[1][:-2]) + [strpSeries(x[1][-2])] + [x[1][-1]])
    ).map(
        # 处理原料数据: 原料理论销量 空值 离群值 取值空值在[q05 与 q95]之间
        # 输入: (微仓 分类 原料id 温区 保质期 城市名称(拼音)) [微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(Series('日期','理论销量') 分类销量(Series('日期','理论销量')]
        # 输出: (微仓 分类 原料id 温区 保质期 城市名称(拼音)) [微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(Series('日期','理论销量') 分类销量(Series('日期','理论销量')]
        lambda x: (x[0], list(x[1][:-2]) + [solve_na_outlier(x[1][-2])] + [x[1][-1]])
    ).map(
        # 输出结果
        # 输入: (微仓 分类 原料id 温区 保质期 城市名称(拼音)) [微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(Series('日期','理论销量') 分类销量(Series('日期','理论销量')]
        # 输出: [微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(Series('日期','理论销量') 分类销量(Series('日期','理论销量')]
        lambda x: x[1]
    )
    mts.persist()  # 暂存

    ''' 打印日志
    rddlog = mts.map(lambda x: x[:8] + [series_tostr(x[8])] + [series_tostr(x[9])]).map(
        lambda x: '\t'.join(map(str, x))
    )
    rddlog.saveAsTextFile('/user/dongsb/algo_log/')

    rddlog = mts.filter(lambda x: x is not None).map(
        lambda x: '\t'.join(map(str, x[1][:3])) + '\t' + x[1][-2] + '\t' + series_tostr(x[1][-1])
    )
    print rddlog.take(1)
    rddlog.saveAsTextFile('/user/dongsb/algo_log/')
    # '''

    # 训练预测
    predict = mts.map(
        # 训练预测
        # 输入: [微仓 分类 原料id 温区 保质期 城市名称 发单批次 促销系数 原料销量(Series('日期','理论销量') 分类销量(Series('日期','理论销量')]
        # 输出: (微仓 分类 原料id 温区 保质期
        #       平均值 方差 中值 应有
        #       mul_real q95 promo slope str(coe.to_dict()))
        lambda x: tran_out(x, predict_date)
    ).repartition(1).toDF(
        # 微仓 分类 原料id 温区 保质期
        # 平均值 方差 中值 应有
        # "percentile", 'q95', 'mul', 'coes', 'coe'
        [
            "vc", "cid", "mid", "store", "sl",
            "mean", "sd", "median", "yb",
            "percentile", 'q95', 'mul', 'coes', 'coe'
        ]
    )
    predict.registerTempTable('predict')  # 注册临时表

    # noinspection SqlDialectInspection
    res = spark.sql(
        # 微仓 分类 原料id 温区 保质期
        # 平均值 方差 中值 应有
        # c.percentile, c.q95, c.mul, c.coes, c.coe
        """
        SELECT
          c.vc, c.cid, c.mid, c.store, c.sl,
          c.mean, c.sd, c.median, bb.yb,
          c.percentile, c.q95, c.mul, c.coes, c.coe
        FROM (
               SELECT
                 aa.vc, aa.mid, sum(aa.yb) yb
               FROM (
                      SELECT
                        CASE
                          WHEN b.vc_undertake IS NULL
                            THEN a.vc
                          ELSE b.vc_undertake
                        END vc,
                        mid,
                        a.yb * nvl(b.scale, 1) yb
                      FROM predict a
                        LEFT JOIN (
                                    -- 微仓迁移
                                    SELECT *
                                    FROM dw.vc_migrate
                                    WHERE dp <= '%s'
                                  ) b ON a.vc = b.vc_close
                    ) aa
               GROUP BY aa.vc, aa.mid
             ) bb
          JOIN predict c ON bb.vc = c.vc AND bb.mid = c.mid
        """ % dp
    )
    res.registerTempTable('res')  # 注册临时表

    # noinspection SqlDialectInspection
    spark.sql(
        """
        INSERT overwrite TABLE {database}.wh_material_info
        PARTITION (dp='{dp}')
        SELECT
          split(vc, '-')[0],
          vc, cid, mid, sl,
          mean, sd, median, yb,
          percentile, q95, mul, coes, coe
        FROM res
        """.format(database=database, dp=dp)
    )
    mts.unpersist()
    # write(spark, dp)  # 写入mysql保存
    return mts_origin, res


def get_tyb(row):
    # (vc, mid, wh, cid, yy, vc_kc, sum(yy), wh_kc, sum(vc_kc)))
    vc, mid, wh, cid, yy, vc_kc, sum_yy, wh_kc, sum_vc_kc, sum_raw_yb = row
    # 微仓应有 - 微仓库存 = 微仓应补

    if wh_kc is None:
        wh_kc = 0

    # @todo 日清瓜分
    # 大仓库存 - 大仓应补 > 0 则不需要瓜分
    if wh_kc - sum_raw_yb >= 0:
        tyb = yy - (vc_kc if vc_kc is not None else 0.0)
        flag = 1  # 用于标识无需瓜分
    else:
        # 大仓库存 不足 时 按微仓应有比例进行库存平均分配
        # total_kc = sum_vc_kc + (wh_kc if wh_kc is not None else 0.0)
        #
        # tyb = round(total_kc * yy / sum_yy - (vc_kc if vc_kc is not None else 0.0))
        tyb = round(wh_kc * yy / float(sum_yy) - (vc_kc if vc_kc is not None else 0.0))
        if tyb < 0:
            tyb = 0
            flag = 1
        else:
            # 继续处理 瓜分不完全的情况
            # print vc, wh_kc, sum_yy, yy, wh_kc * yy / float(sum_yy), vc_kc, tyb
            flag = 0
    # flag = 1 无需后续处理
    # flag = 0 需要二次瓜分
    return (vc, mid), yy, tyb, flag


# noinspection SqlDialectInspection
def inventory_distribute(spark, theoretical_yy, wh_inventory, vc_inventory, last_day):
    # theoretical_yy: (vc, cid, mid, sl, mean, sd, median, yy, percentile, q95, mul, coes, coe)
    # wh_inventory: (wh, mid, kc_sl)
    # vc_inventory: (vc, mid, kc_sl)
    dp, _ = get_other_day(last_day, 0)
    # 微仓原料应有
    vc_theoretical_yy = theoretical_yy.map(
        # 组织key: 微仓编码,原料id
        # 输入: 微仓编码 分类 原料ID sl, mean, sd, median, 应用数量, percentile, q95, mul, coes, coe
        # vc, cid, mid, sl, mean, sd, median, yb, percentile, q95, mul, coes, coe
        # 输出: (微仓编码,原料id),(分类,应有数量)
        lambda x: ((x[0], x[2]), (x[1], x[7]))
    )
    # ((vc, mid), (cid, yy))

    # 大仓原料应有
    wh_theoretical_yy = vc_theoretical_yy.map(
        # 组织key: 大仓编码,原料id
        # 输入: (微仓编码,原料id),(分类,应有数量)
        # 输出: (大仓编码,原料id),应有数量
        lambda x: ((x[0][0].split('-')[0], x[0][1]), x[1][1])
    ).reduceByKey(
        # 应有数量加和
        # 输入:(大仓编码,原料id),应有数量
        # 输出:(大仓编码,原料id),应有数量加和
        lambda x, y: x + y
    )
    # ((wh, mid), sum(yy))

    vc_inventory = vc_inventory.map(
        # 组织key: 微仓编码,原料id
        # 输入: 微仓编码 原料id 逻辑库存
        # 输出: (微仓编码,原料id),逻辑库存
        lambda x: ((x[0], x[1]), x[2])
    )
    # ((vc, mid), kc)

    # 换算大仓逻辑库存
    vc_inventory_sum = vc_inventory.map(
        # 组织key: (大仓编码,原料id),逻辑库存
        # 输入: (微仓编码,原料id),逻辑库存
        # 输出: (大仓编码,原料id),逻辑库存
        lambda x: ((x[0][0].split('-')[0], x[0][1]), x[1])
    ).reduceByKey(lambda x, y: x + y)
    # ((wh, mid), sum(vc_kc))

    vc_info = vc_theoretical_yy.leftOuterJoin(vc_inventory).map(
        # 输入: (微仓编码,原料id),[(分类,应有数量),逻辑库存]
        # 输出: 微仓编码，原料id，分类，应有数量，逻辑库存
        lambda x: (x[0][0], x[0][1], x[1][0][0], x[1][0][1], (x[1][1] if x[1][1] is not None else 0))
    )
    # (vc, mid, cid, yy, vc_kc)

    wh_raw_yb = vc_info.map(
        # 输入: 微仓编码，原料id，分类，应有数量，逻辑库存
        # 输出: (大仓编码,原料id),应补数量(应有数量-逻辑库存)
        lambda x: ((x[0].split('-')[0], x[1]), (x[3] - x[4] if x[3] - x[4] > 0 else 0))
    ).reduceByKey(
        # 累加 应补数量
        # 输出: (大仓编码,原料id),应补数量加和
        lambda x, y: x + y
    )
    # ((wh, mid), sum(raw_yb))

    wh_inventory = wh_inventory.map(
        # 输入: 大仓编码,原料id,逻辑库存
        # 输出: (大仓编码,原料id),大仓逻辑库存
        lambda x: ((x[0], x[1]), x[2] if x[2] is not None else 0)
    )
    wh_info = wh_theoretical_yy.leftOuterJoin(wh_inventory).map(
        # 输入: (大仓编码,原料ID),[应有数量加和,逻辑库存]
        # 输出：(大仓编码,原料ID),(应有数量，逻辑库存)
        lambda x: ((x[0][0], x[0][1]), (x[1][0], x[1][1]))
    ).leftOuterJoin(wh_raw_yb).map(
        # 输入: (大仓编码,原料id),[(应有数量，逻辑库存),应补数量加和]
        # 输出: (大仓编码,原料id),(应有数量,逻辑库存,应补数量加和)
        lambda x: (x[0], (x[1][0][0], x[1][0][1], x[1][1]))
    )
    # ((wh, mid), (sum(yy), wh_kc, sum(raw_yb)))

    vc_info = vc_info.map(
        # 输入: 微仓编码，原料id，分类，应有数量，逻辑库存
        # 输出: (大仓编码,原料id),(微仓编码,分类,应有数量,逻辑库存)
        lambda x: ((x[0].split('-')[0], x[1]), (x[0], x[2], x[3], x[4]))
    ).leftOuterJoin(
        # 输出: (大仓编码,原料id),[(微仓编码,分类,应有数量,逻辑库存),(应有数量，逻辑库存,应补数量)]
        wh_info
    ).leftOuterJoin(
        # 输出：(大仓编码,原料id),[[(微仓编码,分类,应有数量,逻辑库存),(应有数量，逻辑库存,应补数量)],逻辑库存加和]
        vc_inventory_sum
    ).map(
        # 输出: 微仓编码,原料ID,大仓编码,分类,微仓应有数量,微仓逻辑库存,微仓应有数量加和,大仓逻辑库存,微仓逻辑库存加和,微仓应补数量加和
        lambda x: (
            x[1][0][0][0], x[0][1], x[0][0], x[1][0][0][1], x[1][0][0][2],
            x[1][0][0][3], x[1][0][1][0], x[1][0][1][1], x[1][1], x[1][0][1][2]
        )
    )
    # (vc, mid, wh, cid, yy, vc_kc, sum(yy), wh_kc, sum(vc_kc), sum(raw_yb))
    #   0   1    2   3    4    5      6        7        8            9
    # print '==============vc_info==============', vc_info.collect()
    # 开始计算应补与瓜分

    tmp_tyb = vc_info.map(get_tyb)

    # ((vc, mid), yy, tyb, flag)
    vc_yb = tmp_tyb.filter(
        # 过滤二次瓜分
        # (vc, mid), yy, tyb, flag
        lambda x: x[3] == 1
    ).map(
        # 输出: 微仓编码, 应有数量,理论应补数量
        lambda x: (x[0][0], x[0][1], float(x[2]))
    )
    # print '==============vc_yb==============', vc_yb.collect()
    vc_yb.persist()  # 不需要二次瓜分

    vc_tyb = tmp_tyb.filter(
        lambda x: x[3] == 0
    ).map(
        # 输出: 微仓编码,原料id,应有数量,理论应补数量
        lambda x: (x[0][0], x[0][1], x[1], x[2])
    )  # 需要二次瓜分
    # (vc, mid, yy, tyb)
    # print '==============vc_tyb==============', vc_tyb.collect()

    vc_tyb_diff = vc_tyb.map(
        # 输入: (vc, mid, yy, tyb)
        # 输出: (大仓编码,原料id),理论应补
        lambda x: ((x[0].split('-')[0], x[1]), x[3])
    ).reduceByKey(lambda x, y: x + y).join(wh_inventory).map(
        # 输入: (大仓编码,原料id),[大仓理论应补加和,大仓逻辑库存]
        # 输出: (大仓编码,原料id),剩余不能瓜分干净的库存(大仓理论应补加和 - 大仓逻辑库存)
        lambda x: (x[0], (x[1][1] - x[1][0]))
    )
    # print '==============diff==============', vc_tyb_diff.collect()

    vc_count = vc_tyb.map(
        # 输入: (vc, mid, yy, tyb)
        # 输出: (大仓编码,原料id),1
        lambda x: ((x[0].split('-')[0], x[1]), 1)
    ).reduceByKey(
        # 输入: (大仓编码,原料id),1
        # 输出: (大仓编码,原料id),大仓汇总数量
        lambda x, y: x + y
    )  # 计算需要二次瓜分的原料数量
    wh_residue = vc_count.join(vc_tyb_diff).map(
        # 输入: (大仓编码,原料id),[大仓汇总微仓数量,不能瓜分干净的大仓库存]
        # 输出: (大仓编码,原料id),(平均每个微仓应补,余下数量)
        lambda x: (x[0], (int(x[1][1] / x[1][0]), int(x[1][1] % x[1][0])))
    )  # 计算大仓残余
    # ((wh, mid), (extra_yb_per_vc, residue_yb))

    order_index_added = vc_tyb.map(
        # 输入: 微仓编码,原料id,应有数量,理论应补数量
        # 输出: (大仓编码,原料id,应有数量),(微仓编码,理论应补数量)
        lambda x: ((x[0].split('-')[0], x[1], x[2]), (x[0], x[3]))
    ).sortByKey(ascending=False).zipWithIndex().map(
        # 输入:((大仓编码,原料id,应有数量),(微仓编码,理论应补数量)),index
        # 输出: (大仓编码,原料id),(微仓编码,应有数量,理论应补数量,index)
        lambda x: ((x[0][0][0], x[0][0][1]), (x[0][1][0], x[0][0][2], x[0][1][1], x[1]))
    )
    # ((wh, mid), (vc, yy, tyb, index))
    # print '==============order_index_added==============', order_index_added.collect()
    start_index = order_index_added.reduceByKey(
        # 输入: (大仓编码,原料id),(微仓编码,应有数量,理论应补数量,index)
        # 输出: (大仓编码,原料id),(微仓编码,理论应补数量最小值,理论应补数量,index)
        lambda x, y: (x[0], x[1], min(x[2], y[2]), x[3])
    ).map(
        # 输出: (大仓编码,原料id),理论应补数量最小值
        lambda x: (x[0], x[1][2])
    )

    # ((wh, mid), min_index)
    # print '==============start_index==============', start_index.collect()
    # print '==============order_index_added==============', order_index_added.leftOuterJoin(start_index) \
    #     .map(lambda x: (x[0], (x[1][0][0], x[1][0][2], x[1][0][3] - x[1][1]))) \
    #     .leftOuterJoin(wh_residue).collect()

    ''' 打印日志
    rddlog = res.map(
        lambda x: "\t".join(map(str, x))
    )
    rddlog.saveAsTextFile('/user/dongsb/algo_log/')
    return
    # '''

    def oc(row):
        result = None
        if row[1][1] is None:
            (wh, mid), ((vc, vc_tyb, xx), _) = row
            result = vc, mid, vc_tyb
        else:
            # (大仓编码,原料id),[(微仓编码,微仓理论应补,x) ,(平均每个微仓应补,余下数量)]
            (wh, mid), ((vc, vc_tyb, xx), (vc_avyb, leave)) = row
            result = vc, mid, vc_tyb + vc_avyb + (1 if xx < leave else 0)
        return result

    res = order_index_added.leftOuterJoin(start_index).map(
        # 输入: (大仓编码,原料id),[(微仓编码,应有数量,微仓理论应补数量,index),理论应补数量最小值]
        # 输出: (大仓编码,原料id),(微仓编码,微仓理论应补,x)
        lambda x: (x[0], (x[1][0][0], x[1][0][2], x[1][0][3] - x[1][1]))
    ).leftOuterJoin(wh_residue).map(
        # 输入: (大仓编码,原料id),[(微仓编码,微仓理论应补,x) ,(平均每个微仓应补,余下数量)]
        # 输出: 微仓编码,原料id,微仓理论应补 + 平均每个微仓应补 +
        # lambda x: (x[1][0][0], x[0][1], x[1][0][1] + x[1][1][0] + (1 if x[1][0][2] < x[1][1][1] else 0))
        oc
    ).union(vc_yb).toDF(['vc', 'mid', 'yb'])
    # print '==============res==============', res.collect()

    res.registerTempTable('yb')
    spark.sql("""
        INSERT overwrite TABLE supply.wh_material_yb
        partition(dp='%s')
        SELECT * FROM yb
    """ % dp)


def divide_up():
    # 瓜分
    pass


def kurong_cap(row):
    vc, wenqu, mid, yb, daguige, is_riqing, cubage, sum_kc_vol, sum_yb_vol, sum_yb = row
    sum_vol = sum_kc_vol + sum_yb_vol
    if yb == 0 or is_riqing == 1:
        yb = yb
    else:
        if sum_kc_vol >= cubage:
            yb = 0
        elif sum_vol > cubage:
            ava_cub = cubage - sum_kc_vol
            ratio = ava_cub / sum_yb_vol
            yb = yb * ratio
            if daguige > 0:
                yb = math.floor(yb / daguige) * daguige
            yb = round(yb)
        else:
            yb = yb
    return vc, mid, yb


def kurong_vc(spark, theoretical_yb, vc_info, last_day):
    # theoretical_yb: (vc, wenqu, cid, mid, vol, kc, yb, yy, daguige, is_riqing)
    # vc_info: (vc, wenqu, cubage, vc_batch)
    # vc,wenqu,sum_yb_vol,sum_kc_vol,sum_yb,cubage

    vc_kc_vol = theoretical_yb.map(lambda x: ((x[0], x[1]), x[5] * x[4])).reduceByKey(lambda x, y: x + y)

    vc_yb_vol = theoretical_yb.map(lambda x: ((x[0], x[1]), x[6] * x[4])).reduceByKey(lambda x, y: x + y)

    vc_yb_sum = theoretical_yb.map(lambda x: ((x[0], x[1]), x[6])).reduceByKey(lambda x, y: x + y)

    # vc,wenqu,cubage,sum_kc_vol,sum_yb_vol,sum_yb
    vc_wenqu_vol = vc_info.map(
        lambda x: ((x[0], x[1]), x[2])
    ).leftOuterJoin(
        vc_kc_vol
    ).leftOuterJoin(
        vc_yb_vol
    ).leftOuterJoin(
        vc_yb_sum
    ).map(
        lambda x: (x[0][0], x[0][1], x[1][0][0][0], x[1][0][0][1], x[1][0][1], x[1][1])
    )

    # vc, wenqu, mid, yb, daguige, is_riqing, cubage, sum_kc_vol, sum_yb_vol, sum_yb
    theoretical_yb = theoretical_yb.map(
        lambda x: ((x[0], x[1]), (x[3], x[6], x[8], x[9]))
    ).leftOuterJoin(vc_wenqu_vol).map(
        lambda x: (
            x[0][0], x[0][1], x[1][0][0], x[1][0][1],
            x[1][0][2], x[1][0][3], x[1][1][0], x[1][1][1],
            x[1][1][2], x[1][1][3]
        )
    )

    kurong_yb = theoretical_yb.map(kurong_cap)
    return kurong_yb


if __name__ == '__main__':
    os.environ['SPARK_HOME'] = '/data/src/spark'
    sparkConf = SparkConf().setSparkHome(
        '/data/src/spark'
    ).setAppName(
        'wayaya'
    )
    sc = SparkContext(conf=sparkConf)
    sc.addFile('lib.py')
    sc.addFile('conf.py')

    hc = HiveContext(sc)
    last = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    duration = day_span  # 数据天数
    last_day = run_day  # 计算日期
    database = yy_database  # 预测结果保存位置(hive)

    # 返回原料数据与预测结果
    mts_origin, yy = get_data(hc, duration, last_day, database)

    """ 计算应补数量
    # 计算应补数量
    wh_inventory, vc_inventory = get_inventory(hc)  # 获取库存RDD
    dp, _ = get_other_day(last_day, 0)  # 获取当前日期
    # 应有库存
    # 微仓应有 分类 原料id 保质期 平均值 方差 中值
    # noinspection SqlDialectInspection
    yy = hc.sql('''
      SELECT
        vc, cid, mid, sl, mean, sd, median, yb, percentile, q95, mul, coes, coe
      FROM supply.wh_material_info
      WHERE dp='%s'
    ''' % dp)
    yy.persist()  # 应有库存RDD暂存
    # 计算应补数量 瓜分
    inventory_distribute(hc, yy.rdd.repartition(1).map(tuple), wh_inventory, vc_inventory, last_day)
    # 计算售罄指标
    # vc_loss, district_loss, total_loss = saleout_loss(hc, mts_origin)
    # """
    pass
