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

# 更新促销信息 sql 语句
# noinspection SqlDialectInspection
promo_sql = '''
(SELECT
   al.daqu                                                                  AS daqu,
   al.vc_material_id                                                        AS material_id,
   al.new_pinlei                                                            AS category_gbk,
   CASE
   WHEN al.new_pinlei = '轻食'
     THEN 'LIGHT'
   WHEN al.new_pinlei IN ('乳类', '乳品')
     THEN 'DAIRY'
   WHEN al.new_pinlei IN ('小食', '零食', '干果类')
     THEN 'SNACKS'
   WHEN al.new_pinlei LIKE '%%水果%%'
     THEN 'FRUITS'
   WHEN al.new_pinlei IN ('海鲜', '水产')
     THEN 'AQUATIC'
   WHEN al.new_pinlei = '熟食'
     THEN 'DELIS'
   WHEN al.new_pinlei IN ('肉禽', '蛋类', '肉蛋', '战略商品蛋类')
     THEN 'M&E'
   WHEN al.new_pinlei = '粮油'
     THEN 'G&O'
   WHEN al.new_pinlei = '蔬菜'
     THEN 'VEGETABLES'
   WHEN al.new_pinlei IN ('酒类', '酒饮', '饮品')
     THEN 'BEVERAGES'
   WHEN al.new_pinlei = '速食'
     THEN 'INSTANT'
   WHEN al.new_pinlei IN ('日百', '日用品')
     THEN 'COMMODITIES'
   WHEN al.new_pinlei = '赠品'
     THEN 'PRESENTS'
   ELSE al.new_pinlei
   END                                                                         category,
   al.vc_warehouse                                                          AS vc_warehouse,
   al.city                                                                  AS city_gbk,
   CASE
   WHEN al.city LIKE '上海%%'
     THEN 'SHANGHAI'
   WHEN al.city LIKE '深圳%%'
     THEN 'SHENZHEN'
   WHEN al.city LIKE '北京%%'
     THEN 'BEIJING'
   WHEN al.city LIKE '天津%%'
     THEN 'TIANJIN'
   WHEN al.city LIKE '杭州%%'
     THEN 'HANGZHOU'
   WHEN al.city LIKE '苏州%%'
     THEN 'SUZHOU'
   WHEN al.city LIKE '常州%%'
     THEN 'CHANGZHOU'
   WHEN al.city LIKE '宁波%%'
     THEN 'NINGBO'
   WHEN al.city LIKE '合肥%%'
     THEN 'HEFEI'
   WHEN al.city LIKE '南京%%'
     THEN 'NANJING'
   WHEN al.city LIKE '昆山%%'
     THEN 'KUNSHAN'
   WHEN al.city LIKE '南通%%'
     THEN 'NANTONG'
   WHEN al.city LIKE '无锡%%'
     THEN 'WUXI'
   WHEN al.city LIKE '广州%%'
     THEN 'GUANGZHOU'
   WHEN al.city LIKE '东莞%%'
     THEN 'DONGGUAN'
   WHEN al.city LIKE '石家庄%%'
     THEN 'SHIJIAZHUANG'
   WHEN al.city LIKE '青岛%%'
     THEN 'QINGDAO'
   WHEN al.city LIKE '太原%%'
     THEN 'TAIYUAN'
   WHEN al.city LIKE '济南%%'
     THEN 'JINAN'
   WHEN al.city LIKE '廊坊%%'
     THEN 'LANGFANG'
   WHEN al.city LIKE '珠海%%'
     THEN 'ZHUHAI'
   WHEN al.city LIKE '惠州%%'
     THEN 'HUIZHOU'
   WHEN al.city LIKE '佛山%%'
     THEN 'FOSHAN'
   WHEN al.city LIKE '南宁%%'
     THEN 'NANNING'
   WHEN al.city LIKE '唐山%%'
     THEN 'TANGSHAN'
   END                                                                         city,
   SUBSTRING_INDEX(GROUP_CONCAT(al.cs ORDER BY al.id DESC), ',', 1)         AS case_status,
   SUBSTRING_INDEX(GROUP_CONCAT(al.id ORDER BY al.id DESC), ',', 1)         AS id_from_site_coefficient,
   SUBSTRING_INDEX(GROUP_CONCAT(al.new_ratio ORDER BY al.id DESC), ',', 1)  AS promo_ratio,
   SUBSTRING_INDEX(GROUP_CONCAT(al.event_type ORDER BY al.id DESC), ',', 1) AS promo_type,
   al.vc_batch
 FROM
   (SELECT
      u.daqu,
      u.vc_material_id,
      u.new_pinlei,
      u.vc_warehouse,
      u.city,
      u.cs,
      u.id,
      u.new_ratio,
      ifnull(u.event_type, 0) event_type,
      u.vc_batch
    FROM
      (
        -- test case1 1000
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '1000' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NOT NULL AND material_id != '')
                  AND (category IS NULL OR category = '')
                  AND (small_warehouse IS NULL OR small_warehouse = '')
                  AND (city IS NULL OR city = '')
          ) c1
            ON s1.daqu = c1.big_warehouse AND s1.vc_material_id = c1.material_id
        UNION ALL
        -- test case2 1001
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '1001' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NOT NULL AND material_id != '')
                  AND (category IS NULL OR category = '')
                  AND (small_warehouse IS NULL OR small_warehouse = '')
                  AND (city IS NOT NULL AND city != '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_material_id = c1.material_id
               AND s1.city = c1.city
        UNION ALL
        -- test case3 0100
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '0100' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NULL OR material_id = '')
                  AND (category IS NOT NULL AND category != '')
                  AND (small_warehouse IS NULL OR small_warehouse = '')
                  AND (city IS NULL OR city = '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.new_pinlei = c1.category
        UNION ALL
        -- test case4 0101
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '0101' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NULL OR material_id = '')
                  AND (category IS NOT NULL AND category != '')
                  AND (small_warehouse IS NULL OR small_warehouse = '')
                  AND (city IS NOT NULL AND city != '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.new_pinlei = c1.category
               AND s1.city = c1.city
        UNION ALL
        -- test case5 1100
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '1100' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NOT NULL AND material_id != '')
                  AND (category IS NOT NULL AND category != '')
                  AND (small_warehouse IS NULL OR small_warehouse = '')
                  AND (city IS NULL OR city = '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.new_pinlei = c1.category
               AND s1.vc_material_id = c1.material_id
        UNION ALL
        -- test case6 1101
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '1101' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NOT NULL AND material_id != '')
                  AND (category IS NOT NULL AND category != '')
                  AND (small_warehouse IS NULL OR small_warehouse = '')
                  AND (city IS NOT NULL AND city != '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.new_pinlei = c1.category
               AND s1.vc_material_id = c1.material_id
               AND s1.city = c1.city
        UNION ALL
        -- test case7 1010
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '1010' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NOT NULL AND material_id != '')
                  AND (category IS NULL OR category = '')
                  AND (small_warehouse IS NOT NULL AND small_warehouse != '')
                  AND (city IS NULL OR city = '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_warehouse = c1.small_warehouse
               AND s1.vc_material_id = c1.material_id
        UNION ALL
        -- test case8 0110
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '0110' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NULL OR material_id = '')
                  AND (category IS NOT NULL AND category != '')
                  AND (small_warehouse IS NOT NULL AND small_warehouse != '')
                  AND (city IS NULL OR city = '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_warehouse = c1.small_warehouse
               AND s1.new_pinlei = c1.category
        UNION ALL
        -- test case9 0111
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '0111' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END AS city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NULL OR material_id = '')
                  AND (category IS NOT NULL AND category != '')
                  AND (small_warehouse IS NOT NULL AND small_warehouse != '')
                  AND (city IS NOT NULL AND city != '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_warehouse = c1.small_warehouse
               AND s1.new_pinlei = c1.category
               AND s1.city = c1.city
        UNION ALL
        -- test case10 0000
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '0000' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END AS city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NULL OR material_id = '')
                  AND (category IS NULL OR category = '')
                  AND (small_warehouse IS NULL OR small_warehouse = '')
                  AND (city IS NULL OR city = '')
          ) c1
            ON s1.daqu = c1.big_warehouse
        UNION ALL
        -- test case11 0001
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '0001' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END AS city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NULL OR material_id = '')
                  AND (category IS NULL OR category = '')
                  AND (small_warehouse IS NULL OR small_warehouse = '')
                  AND (city IS NOT NULL AND city != '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.city = c1.city
        UNION ALL
        -- test case12 0010
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '0010' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END AS city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NULL OR material_id = '')
                  AND (category IS NULL OR category = '')
                  AND (small_warehouse IS NOT NULL AND small_warehouse != '')
                  AND (city IS NULL OR city = '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_warehouse = c1.small_warehouse
        UNION ALL
        -- test case13 0011
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '0011' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END AS city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NULL OR material_id = '')
                  AND (category IS NULL OR category = '')
                  AND (small_warehouse IS NOT NULL AND small_warehouse != '')
                  AND (city IS NOT NULL AND city != '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_warehouse = c1.small_warehouse
               AND s1.city = c1.city
        UNION ALL
        -- test case14 1011
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '1011' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END AS city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NOT NULL AND material_id != '')
                  AND (category IS NULL OR category = '')
                  AND (small_warehouse IS NOT NULL AND small_warehouse != '')
                  AND (city IS NOT NULL AND city != '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_material_id = c1.material_id
               AND s1.vc_warehouse = c1.small_warehouse
               AND s1.city = c1.city
        UNION ALL
        -- test case15 1110
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '1110' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END AS city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NOT NULL AND material_id != '')
                  AND (category IS NOT NULL AND category != '')
                  AND (small_warehouse IS NOT NULL AND small_warehouse != '')
                  AND (city IS NULL OR city = '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_material_id = c1.material_id
               AND s1.vc_warehouse = c1.small_warehouse
               AND s1.new_pinlei = c1.category
        UNION ALL
        -- test case16 1111
        SELECT
          s1.daqu,
          s1.vc_warehouse,
          s1.new_pinlei,
          s1.vc_material_id,
          c1.new_ratio,
          c1.event_type,
          '1111' cs,
          c1.id,
          s1.city,
          s1.vc_batch
        FROM
          (SELECT
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN 'MRYXSHW'
             ELSE substring_index(vc_warehouse, '-', 1) END daqu,
             CASE WHEN substring_index(vc_warehouse, '-', 1) = 'MRYXSH'
               THEN concat('MRYXSHW-', substring_index(vc_warehouse, '-', -1))
             ELSE vc_warehouse END                          vc_warehouse,
             new_pinlei,
             vc_material_id,
             city,
             vc_batch
           FROM bi_bak.shj_yuanliao_xiaoshou_infor_all_month
           WHERE vc_batch = '{dt}'
          ) s1
          JOIN
          (
            SELECT
              id,
              big_warehouse,
              small_warehouse,
              category,
              material_id,
              CASE WHEN right(city, 1) = '市'
                THEN substring(city, 1, char_length(city) - 1)
              ELSE city END AS city,
              new_ratio,
              event_type,
              first_change_time,
              last_change_time
            FROM bi_dev.site_coefficient
            WHERE status = 0 AND new_ratio != 1
                  AND date_format(first_change_time, '%Y-%m-%d') <= '{dt}'
                  AND date_format(last_change_time, '%Y-%m-%d') >= '{dt}'
                  AND (big_warehouse IS NOT NULL AND big_warehouse != '')
                  AND (material_id IS NOT NULL AND material_id != '')
                  AND (category IS NOT NULL AND category != '')
                  AND (small_warehouse IS NOT NULL AND small_warehouse != '')
                  AND (city IS NOT NULL AND city != '')
          ) c1
            ON s1.daqu = c1.big_warehouse
               AND s1.vc_material_id = c1.material_id
               AND s1.vc_warehouse = c1.small_warehouse
               AND s1.new_pinlei = c1.category
               AND s1.city = c1.city
      ) u
    ORDER BY u.daqu, u.vc_material_id, u.new_pinlei, u.vc_warehouse, u.city
   ) al
 GROUP BY al.daqu, al.vc_material_id, al.new_pinlei, al.vc_warehouse, al.city
) uu
'''


