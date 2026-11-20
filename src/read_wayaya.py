#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 10:31:21 2018

@author: wayaya
"""

from pyspark import SparkConf, SparkContext, HiveContext
from lib import get_other_day
import sys
import os

from conf import run_day, day_span, hive_database
from read_conf import promo_sql


def update_promo_info(spark, i, database):
    # 取前一天的数据
    dp, dt = get_other_day(i, -1)  # 20180502 2018-05-02
    url = 'jdbc:mysql://10.10.131.156:3306'
    prop = {'user': 'bi_u28', 'password': 'ki*safsaHb-d', 'driver': 'com.mysql.jdbc.Driver'}

    table1 = promo_sql.format(dt=dt)
    spark.read.jdbc(url, table1, properties=prop).registerTempTable('info')

    # 写入促销信息
    # noinspection SqlDialectInspection
    # 大仓编码 原料id 品类名称中文 品类名称英文 微仓编码 城市名称中文 城市名称拼音 case_status id_from_site_coefficient 促销力度 促销类型 vc_batch
    spark.sql(
        """
        INSERT overwrite TABLE {database}.wh_vc_promotion_info
        PARTITION (dt = '{dt}')
          SELECT
            daqu,
            material_id,
            category_gbk,
            category,
            vc_warehouse,
            city_gbk,
            city,
            case_status,
            id_from_site_coefficient,
            promo_ratio,
            promo_type,
            vc_batch
          FROM info
        """.format(dt=dt, database=database)
    )


# noinspection SqlDialectInspection
def get_category(spark):
    url = 'jdbc:mysql://10.10.131.156:3306'
    prop = {'user': 'bi_u28', 'password': 'ki*safsaHb-d', 'driver': 'com.mysql.jdbc.Driver'}
    # 'FRUITS', 'VEGETABLES', 'M&E', 'AQUATIC', 'DELIS', 'INSTANT', 'G&O', 'DAIRY',
    # 'SNACKS', 'BEVERAGES', 'LIGHT', 'COMMODITIES', 'PRESENTS'
    # 分类 原料id 原料名称 温区 保质期
    tb = """
        (
          SELECT
              CASE
              WHEN vc_parent_category_name = '轻食' THEN 'LIGHT'
              WHEN vc_parent_category_name IN ('乳类', '乳品') THEN 'DAIRY'
              WHEN vc_parent_category_name IN ('小食', '零食', '干果类') THEN 'SNACKS'
              WHEN vc_parent_category_name LIKE '%%水果%%' THEN 'FRUITS'
              WHEN vc_parent_category_name IN ('海鲜', '水产') THEN 'AQUATIC'
              WHEN vc_parent_category_name = '熟食' THEN 'DELIS'
              WHEN vc_parent_category_name IN ('肉禽', '蛋类', '肉蛋', '战略商品蛋类') THEN 'M&E'
              WHEN vc_parent_category_name = '粮油' THEN 'G&O'
              WHEN vc_parent_category_name = '蔬菜' THEN 'VEGETABLES'
              WHEN vc_parent_category_name IN ('酒类', '酒饮', '饮品') THEN 'BEVERAGES'
              WHEN vc_parent_category_name = '速食' THEN 'INSTANT'
              WHEN vc_parent_category_name IN ('日百', '日用品') THEN 'COMMODITIES'
              WHEN vc_parent_category_name = '赠品' THEN 'PRESENTS'
              ELSE vc_parent_category_name
              END                                                                              cid,
              vc_internal_id                                                                   mid,
              vc_name                                                                          name,
              vc_store_condition                                                               store,
              (
                CASE
                WHEN (
                  (l_shelf_life IS NULL AND l_shelf_life_hour IS NULL)
                  OR (IFNULL(l_shelf_life, 0) + IFNULL(l_shelf_life_hour, 0) / 24) = 0
                )
                  THEN (
                    CASE WHEN l_turnover_day IS NULL
                      THEN 1
                    ELSE l_turnover_day
                    END
                  )
                ELSE (IFNULL(l_shelf_life, 0) + IFNULL(l_shelf_life_hour, 0) / 24 - 1) / 2
                END
              ) sl
          FROM dw_ods.bms_ods_bms_material
        ) AS tb3
        """
    category = spark.read.jdbc(url, tb, properties=prop)
    category.registerTempTable('category')
    return category


# mysql -h 10.10.131.156 -u bi_u28 -pki*safsaHb-d
# noinspection SqlDialectInspection
def read1(spark, duration, i, database):
    # 取前一天
    dp, dt = get_other_day(i, -1)  # 20180502 2018-05-02
    print 'date: ', dp
    begin_dp, begin_dt = get_other_day(i, -duration)

    end_dp, end_dt = get_other_day(i, -1)

    url = 'jdbc:mysql://10.10.131.156:3306'
    prop = {'user': 'bi_u28', 'password': 'ki*safsaHb-d', 'driver': 'com.mysql.jdbc.Driver'}

    # 销量信息
    # 微仓编码 原料id 销售出库(物理销量) 理论销量 库存数量 销毁出库(报损) 售罄占比(实际销量/前四周平均天销量) 表负责人:宋厚健
    table1 = """
             (
              SELECT
                  vc_warehouse   vc,
                  vc_material_id mid,
                  l_xsck_sl      sr,
                  lilunxiaoliang tsr,
                  l_kc_sl        kc,
                  l_xhck_sl      xh,
                  zhanbi         zb
                FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
                WHERE vc_batch = '%s'
             ) as tb1
             """ % dt
    spark.read.jdbc(url, table1, properties=prop).registerTempTable('info')

    # 到货信息
    # 微仓编号 原料id 实际补货数量 实际到货数量 表负责人：韩博帅
    table2 = """
               (
                SELECT vc_kqmc vc,
                       material_id mid,
                       l_sjbhsl fh,
                       l_sdhsl dh
                FROM dw_mryx.daohuo_moni_daily
                WHERE f_date = '%s'
              ) AS tb2
             """ % dt
    spark.read.jdbc(url, table2, properties=prop).registerTempTable('res')

    # 微仓改名
    spark.sql(
        "SELECT origin,after FROM dw.north_vc_change"
    ).toDF('origin', 'after').registerTempTable('da')

    # 大仓 微仓 原料ID 实际销量 理论销量 物理库存 销毁 占比 实际补货 实际到货
    spark.sql(
        """
        -- 关联微仓改名信息
        SELECT
          CASE
          WHEN da.after IS NULL
            THEN aa.wh
          ELSE split(da.after, '-')[0]
          END wh,
          CASE
          WHEN da.after IS NULL
            THEN aa.vc
          ELSE da.after
          END vc,
          aa.mid, aa.sr, aa.tsr, aa.kc, aa.xh, aa.zb, aa.fh, aa.dh
        FROM (
               -- 关联到货信息
               SELECT
                 CASE
                 WHEN split(a.vc, '-')[0] = 'MRYXSH'
                   THEN 'MRYXSHW'
                 ELSE split(a.vc, '-')[0]
                 END             wh,
                 CASE
                 WHEN split(a.vc, '-')[0] = 'MRYXSH'
                   THEN concat('MRYXSHW-', split(a.vc, '-')[1])
                 ELSE a.vc
                 END             vc,
                 a.mid,
                 a.sr,
                 round(a.tsr, 2) tsr,
                 a.kc,
                 nvl(a.xh, 0)    xh,
                 a.zb,
                 nvl(b.fh, 0)    fh,
                 nvl(b.dh, 0)    dh
               FROM info a LEFT JOIN res b ON a.vc = b.vc AND a.mid = b.mid
             ) aa LEFT JOIN da ON aa.vc = da.origin
        """
    ).registerTempTable('result')  # 注册临时表

    category = get_category(spark)  # 获取原料以及分类信息
    category.persist()
    category.registerTempTable('category')  # 注册临时表

    # 数据join 后去重
    # 大仓编码 微仓编码 分类 原料id 原料名称 温区 保质期
    # 销量 理论销量 物理库存 销毁 占比 实际补货 实际到货
    spark.sql(
        """
        SELECT
          a.wh, a.vc, b.cid, a.mid, b.name, b.store, b.sl,
          a.sr, a.tsr, a.kc, a.xh, a.zb, a.fh, a.dh
        FROM (
               SELECT
                 wh, vc, mid, sr, tsr, kc, xh, zb, fh, dh,
                 row_number() OVER(PARTITION BY wh, vc, mid ORDER BY kc) num
               FROM result
             ) a LEFT JOIN category b ON a.mid = b.mid
        WHERE a.num <= 1
        """
    ).distinct().repartition(1).registerTempTable('sr')

    # 原料销量数据 写入hive临时表中
    # 大仓编码 微仓编码 分类 原料id 原料名称 温区 保质期
    # 销量 理论销量 物理库存 销毁 占比 实际补货 实际到货
    spark.sql(
        """
        INSERT overwrite TABLE {database}.wh_vc_info_new
        PARTITION (dp = '{dp}')
        SELECT * FROM sr
        """.format(dp=dp, database=database)
    )

    # 读取站长购买信息
    table3 = """
        (
        SELECT
          small_warehouse vc,
          material_id     mid,
          buy_num,
          STATUS,
          buy_date
        FROM bi_dev.abnormal_buy
        WHERE STATUS = 0
        ) as tb3
    """
    spark.read.jdbc(url, table3, properties=prop).registerTempTable('abnorbuy')

    # 处理原料数据 促销信息,消除站长购买,平行仓信息
    # 大仓编号 微仓编号 原料id 原料销量(实际销量#理论销量#促销系数#20180501)
    mts = spark.sql(
        """
        -- 原料销量与历史促销信息
        SELECT
          vi.wh,
          vi.vc,
          vi.mid,
          concat(vi.sr, '#', vi.tsr, '#', nvl(p.promo_ratio, 1), '#', vi.dp) sr
        FROM (
               -- 原料销量关联平行仓, 消除站长购买的影响
               SELECT
                 v.wh,
                 v.vc,
                 v.mid,
                 v.sr - nvl(ab.buy_num, 0) sr,
                 CASE
                 WHEN v.sr < v.tsr AND ab.status IS NOT NULL
                   THEN sr - ab.buy_num
                 ELSE tsr - nvl(ab.buy_num, 0)
                 END                       tsr,
                 v.dp
               FROM (
                      -- 原料销量关联平行仓
                      SELECT
                        (
                          CASE WHEN b.new_vc IS NOT NULL
                            THEN b.new_vc
                          ELSE a.vc
                          END
                        )     vc,
                        (
                          CASE WHEN b.new_vc IS NOT NULL
                            THEN split(b.new_vc, '-')[0]
                          ELSE split(a.vc, '-')[0]
                          END
                        )     wh,
                        a.mid mid,
                        a.sr  sr,
                        a.tsr tsr,
                        a.dp  dp
                      FROM (
                             SELECT *
                             FROM dw.wh_vc_info_new
                             WHERE dp >= '{begin_dp}' AND dp <= '{end_dp}'
                           ) a LEFT JOIN dw.parallel_trans b ON a.vc = b.vc
                    ) v
                 LEFT JOIN (
                             -- 站长购买关联平行仓
                             SELECT
                               (
                                 CASE WHEN b.new_vc IS NOT NULL
                                   THEN b.new_vc
                                 ELSE a.vc
                                 END
                               ) vc,
                               mid,
                               buy_num,
                               status,
                               buy_date
                             FROM abnorbuy a LEFT JOIN dw.parallel_trans b ON a.vc = b.vc
                             WHERE status = 0
                           ) ab ON v.vc = ab.vc AND v.mid = ab.mid
                                   AND v.dp = concat(substr(ab.buy_date, 1, 4), substr(ab.buy_date, 6, 2), substr(ab.buy_date, 9, 2))
             ) vi
          LEFT JOIN (
                      -- 促销信息关联平行仓
                      SELECT
                        (
                          CASE WHEN b.new_vc IS NOT NULL
                            THEN b.new_vc
                          ELSE a.vc_warehouse
                          END
                        )                       vc_warehouse,
                        a.material_id           material_id,
                        a.promo_ratio           promo_ratio,
                        date_add(a.vc_batch, 1) vc_batch
                      FROM (
                             -- 促销信息
                             SELECT *
                             FROM dw.wh_vc_promotion_info
                             WHERE
                               dt >= date_sub('{begin_dt}', 1) AND dt <= date_sub('{end_dt}', 1) AND promo_type = 1
                           ) a LEFT JOIN dw.parallel_trans b ON a.vc_warehouse = b.vc
                    ) p ON vi.vc = p.vc_warehouse
                                   AND vi.mid = p.material_id
                                   AND vi.dp = concat(substr(p.vc_batch, 1, 4), substr(p.vc_batch, 6, 2), substr(p.vc_batch, 9, 2))
        """.format(begin_dp=begin_dp, end_dp=end_dp, begin_dt=begin_dt, end_dt=end_dt)
    ).map(
        # 将DataFrame结果转化为 tuple
        # 输入: 大仓编号 微仓编号 原料id 原料销量(实际销量#理论销量#促销系数#20180501)
        # 输出: (大仓编号 微仓编号 原料id) 原料销量(实际销量#理论销量#促销系数#20180501)
        lambda x: ((x[0], x[1], x[2]), x[3])
    ).reduceByKey(
        # 将不同天的数据使用##拼接起来
        # 输入: (大仓编号 微仓编号 原料id) 原料销量(实际销量#理论销量#促销系数#20180501)
        # 输出: (大仓编号 微仓编号 原料id) 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502)
        lambda x, y: x + '##' + y
    ).map(
        # 对拼接后的原料销量按日期排序
        # 输入: (大仓编号 微仓编号 原料id) 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502)
        # 输出: (大仓编号 微仓编号 原料id) 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502)
        lambda x: (x[0], '##'.join(sorted(x[1].split('##'), key=lambda x: x.split('#')[-1])))
    ).map(
        # 整理数据格式
        # 输入: (大仓编号 微仓编号 原料id) 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502)
        # 输出: 大仓编号 微仓编号 原料id 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502)
        lambda x: (x[0][0], x[0][1], x[0][2], x[1])
    ).repartition(100)
    # 大仓编号 微仓编号 原料id 原料销量(实际销量#理论销量#促销系数#20180501##实际销量#理论销量#促销系数#20180502)
    mts.toDF(['wh', 'vc', 'mid', 'sr']).registerTempTable('mts')

    # 分类数据 关联平行仓
    # 大仓编号 微仓编号 分类 分类数据(实际销量#理论销量#日期)
    cts = spark.sql(
        """
        SELECT
          (
            CASE WHEN b.new_vc IS NOT NULL
              THEN split(b.new_vc, '-')[0]
            ELSE split(a.vc, '-')[0]
            END
          ) wh,
          (
            CASE WHEN b.new_vc IS NOT NULL
              THEN b.new_vc
            ELSE a.vc
            END
          ) vc,
          a.cid,
          a.ts
        FROM (
               SELECT
                 wh, vc, cid,
                 concat(round(mean(sr), 2), '#', round(mean(tsr), 2), '#', dp) ts
               FROM dw.wh_vc_info_new
               WHERE sr > 0 AND dp <= '{end_dp}'
               GROUP BY dp, wh, vc, cid
             ) a LEFT JOIN dw.parallel_trans b ON a.vc = b.vc
        """.format(end_dp=end_dp)
    ).map(
        # 输入: 大仓编号 微仓编号 分类 分类数据(实际销量#理论销量#日期)
        # 输出: (大仓编号,微仓编号,分类),分类数据(实际销量#理论销量#日期)
        lambda x: ((x[0], x[1], x[2]), x[3])
    ).reduceByKey(
        # 汇总数据
        # 输出: (大仓编号,微仓编号,分类),分类数据(实际销量#理论销量#20180501##实际销量#理论销量#20180501)
        lambda x, y: x + '##' + y
    ).map(
        # 对分类数据排序
        # 输出: (大仓编号,微仓编号,分类),分类数据(实际销量#理论销量#20180501##实际销量#理论销量#20180501)
        lambda x: (x[0], '##'.join(sorted(x[1].split('##'), key=lambda x: x.split('#')[-1])))
    ).map(
        # 组织数据
        # 输出: 大仓编号,微仓编号,分类,分类数据(实际销量#理论销量#20180501##实际销量#理论销量#20180501)
        lambda x: (x[0][0], x[0][1], x[0][2], x[1])
    ).repartition(1)
    cts.toDF(['wh', 'vc', 'cid', 'sr']).registerTempTable('cts')

    url_psm = 'jdbc:mysql://10.10.120.27:3306/psm'
    prop_psm = {'user': 'psm', 'password': 'dcnKXANtwo5dZUPL', 'driver': 'com.mysql.jdbc.Driver'}

    tb = '''(
        SELECT
          id vc,
          (
            CASE
           WHEN city LIKE '上海%%' THEN 'SHANGHAI'
           WHEN city LIKE '深圳%%' THEN 'SHENZHEN'
           WHEN city LIKE '北京%%' THEN 'BEIJING'
           WHEN city LIKE '天津%%' THEN 'TIANJIN'
           WHEN city LIKE '杭州%%' THEN 'HANGZHOU'
           WHEN city LIKE '苏州%%' THEN 'SUZHOU'
           WHEN city LIKE '常州%%' THEN 'CHANGZHOU'
           WHEN city LIKE '宁波%%' THEN 'NINGBO'
           WHEN city LIKE '合肥%%' THEN 'HEFEI'
           WHEN city LIKE '南京%%' THEN 'NANJING'
           WHEN city LIKE '昆山%%' THEN 'KUNSHAN'
           WHEN city LIKE '南通%%' THEN 'NANTONG'
           WHEN city LIKE '无锡%%' THEN 'WUXI'
           WHEN city LIKE '广州%%' THEN 'GUANGZHOU'
           WHEN city LIKE '东莞%%' THEN 'DONGGUAN'
           WHEN city LIKE '石家庄%%' THEN 'SHIJIAZHUANG'
           WHEN city LIKE '青岛%%' THEN 'QINGDAO'
           WHEN city LIKE '太原%%' THEN 'TAIYUAN'
           WHEN city LIKE '济南%%' THEN 'JINAN'
           WHEN city LIKE '廊坊%%' THEN 'LANGFANG'
           WHEN city LIKE '珠海%%' THEN 'ZHUHAI'
           WHEN city LIKE '惠州%%' THEN 'HUIZHOU'
           WHEN city LIKE '佛山%%' THEN 'FOSHAN'
           WHEN city LIKE '南宁%%' THEN 'NANNING'
           WHEN city LIKE '唐山%%' THEN 'TANGSHAN'
           END
          )  city
        FROM psm.master_warehouse
    ) AS tb
    '''
    spark.read.jdbc(url_psm, tb, properties=prop_psm).registerTempTable('vc_city_info')

    # 输出原料销量 关联城市名称与分类 并最终写入
    spark.sql(
        """
        INSERT overwrite TABLE {database}.wh_vc_ts
        SELECT
          a.wh, a.vc, b.cid, a.mid,
          b.name, b.store, b.sl, c.city,
          a.sr
        FROM mts a LEFT JOIN category b ON a.mid = b.mid
          LEFT JOIN vc_city_info c ON a.vc = c.vc
        """.format(database=database)
    )

    # 输出分类销量
    spark.sql("""
        insert overwrite table {database}.wh_vc_category_ts
         partition(periods = 'all')
         select * from cts
    """.format(database=database))


if __name__ == '__main__':
    os.environ['SPARK_HOME'] = '/data/src/spark'
    sparkConf = SparkConf().setSparkHome(
        '/data/src/spark'
    ).setAppName(
        'read wayaya'
    )
    sc = SparkContext(conf=sparkConf)
    sc.addFile('lib.py')
    sc.addFile('read_conf.py')
    hc = HiveContext(sc)

    last = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    duration = day_span
    last_day = run_day  # 最后一天的日期
    database = hive_database  # 数据保存的hive库

    update_promo_info(hc, last_day, database)
    read1(hc, duration, last_day, database)
