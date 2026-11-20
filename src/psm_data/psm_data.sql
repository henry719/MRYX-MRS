
-- 闭店日期
SELECT
  blg, -- 日期
  `value` -- 说明
FROM psm_holidays_config where `value` LIKE '%休';


-- 大仓列表
SELECT
  t.id, -- 大仓编码
  t.name, -- 大仓名称
  t.warehouse_live, -- 生存周期
  t.city -- 城市名称
FROM master_warehouse t
WHERE type = 'ZC' AND delete_flag = FALSE;


-- 大仓原料7日平均销量,为计算原料等级准备
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


-- 15天内原料的最早售卖日期
SELECT
  substring_index(t.warehouse, '-', 1) AS daqu, -- 大仓编码
  t.material_id, -- 原料id
  MIN(t.batch)                         AS batch -- 批次日期
FROM
  psm_sales_data t
WHERE t.create_date > date_sub(curdate(), INTERVAL 15 DAY)
      AND t.warehouse LIKE '%-%'
GROUP BY substring_index(t.warehouse, '-', 1), t.material_id;


-- 查询今天已补数量
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


-- 主料与商品
SELECT
  t.sku, -- 商品sku
  t.material -- 原料id
FROM psm_buhuo_m2m_skus t;

-- 原料与商品
SELECT
  t.sku_id,
  t.materials_id
FROM master_bom t
WHERE t.sku_id = 'P-BXSWY-200g';


-- 辅料列表
SELECT
  a.sku_id,
  a.materials_id
FROM master_bom a LEFT JOIN psm_buhuo_m2m_skus b ON a.sku_id = b.sku AND a.materials_id = b.material
WHERE b.material IS NULL;


-- 两天内微仓订单数量
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
GROUP BY t.warehouse_code;


-- 仓库（大仓、微仓）一周内品类销量
SELECT
  t.warehouse_code, -- 微仓编码
  t.category, -- 品类
  ROUND(avg(t.qty), 0) AS qty -- 平均单量
FROM psm_riqi_cangku_pinlei_xiaoliang t
WHERE t.batch > date_sub(curdate(), INTERVAL 8 DAY) AND t.batch < curdate()
GROUP BY t.category, t.warehouse_code;


--  微仓七日平均订单量,为微仓站点等级准备
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


-- 新品促销品
SELECT
  t.batch, -- 日期
  t.material, -- 原料id
  t.city, -- 城市
  t.daqu, -- 大仓编码
  b.materials_name, -- 原料名称
  b.turnover_days, -- 周转天数
  b.store_condition -- 温区
FROM psm_active_configure t LEFT JOIN master_materials b ON t.material = b.materials_id
WHERE t.batch = date_add(curdate(), INTERVAL 1 DAY);


-- 干仓预留
SELECT
  t.warehouse, -- 大仓编码
  t.ip_addr, -- url ip
  t.ip_port, -- 端口号
  t.ip_user, -- 用户名
  t.ip_pass, -- 密码
  t.system_info
FROM master_wms_ip_config t
WHERE warehouse IN (
  -- 大仓列表
  SELECT t.id AS wh -- 大仓编码
  FROM master_warehouse t
  WHERE type = 'ZC' AND delete_flag = FALSE
);


-- 核心算法计算结果,微仓原料应有数量
SELECT
  vc  AS warehouse_id, -- 微仓编码
  mid AS material_id, -- 原料id
  yb  AS shouldbe_qty -- 应有数量
FROM wh_material_info;


-- 需要补货的微仓,活动微仓,此数据将作为补货的基础数据
SELECT
  t.warehouse AS vc, -- 微仓编码
  w.city      AS city, -- 城市
  w.name      AS name -- 微仓名称
FROM (
       -- 在售微仓
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
ORDER BY vc DESC;


-- 微仓 本阜、外阜 标记 订单量
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


-- 微仓 本阜、外阜 品类销量
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
  ) a LEFT JOIN
  (
    -- 本阜、外阜标记
    SELECT
      t.warehouse_id, -- 微仓编码
      t.city, -- 城市名称
      t.value -- 本埠:BF 外阜:WF
    FROM psm_rule_map t
    WHERE t.del_flag = FALSE
          AND t.type = 'benfuWaifu'
  ) b ON a.city = b.city
    LEFT JOIN
    (
      -- 最近7天品类销量
      SELECT
        t.warehouse_code     AS vc, -- 微仓编码
        t.category, -- 品类
        ROUND(avg(t.qty), 0) AS qty
      FROM psm_riqi_cangku_pinlei_xiaoliang t
      WHERE batch < curdate() AND batch >= date_sub(curdate(), INTERVAL 8 DAY)
      GROUP BY t.category, vc
    ) c ON a.vc = c.vc;


-- 大仓在售列表、周转天数
SELECT
  a.wh, -- 大仓编码
  a.materials_id, -- 原料id
  a.category, -- 品类
  a.materials_name, -- 原料名称
  CASE
  WHEN b.turnover IS NOT NULL
    THEN b.turnover
  ELSE a.turnover_days
  END AS turnover, -- 周转天数
  a.store_condition -- 温区
FROM
  (
    SELECT DISTINCT
      m.category, -- 品类
      m.materials_id, -- 原料id
      m.materials_name, -- 原料名称
      m.turnover_days, -- 周转
      m.store_condition, -- 温区
      mcw.warehouse AS wh -- 大仓编码
    FROM
      master_category c JOIN master_category_sku s
        ON c.category_id = s.category_id AND c.is_chrome = TRUE AND c.active = TRUE
      JOIN master_bom b ON s.sku_id = b.sku_id
      JOIN master_materials m ON b.materials_id = m.materials_id AND m.turnover_days IS NOT NULL
      JOIN bms_product bp ON bp.goods_no = b.sku_id AND bp.goods_status = 1 AND bp.goods_status = 1
      LEFT JOIN master_category_warehouse mcw ON c.category_id = mcw.category_id AND mcw.is_liansuodian = FALSE
  ) a LEFT JOIN
  (
    -- 原料周转天数
    SELECT
      material_id AS mid, -- 原料id
      daqu        AS wh, -- 大仓编码
      `value`     AS turnover -- 周转天数
    FROM psm_rule_map
    WHERE type = 'yuanliaoZhouzhuantianshu'
          AND del_flag = FALSE
  ) b ON a.materials_id = b.mid and a.wh = b.wh;


-- 新品促销品
-- new_promo_sku.txt


-- 补货批次配置
SELECT
  category_id, -- 品类
  store_condition_code, -- 温区
  bch2, -- 拣货批次
  material_id, -- 原料id
  daqu, -- 大仓编码
  benfu_waifu, -- 本阜、外阜
  cast(`value` AS SIGNED) % 24 as hour -- 批次时间
FROM psm_rule_map
WHERE type = 'buhuoPici' AND del_flag = FALSE;

-- 批次数据
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
WHERE type = 'buhuoPici' AND del_flag = FALSE;


-- 外阜标记
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
WHERE type = 'benfuWaifu' AND del_flag = FALSE;



-- 微仓详情
SELECT
  t.id, -- 仓库编号
  t.name, -- 仓库名称
  t.warehouse_live,
  t.type, -- 仓库类型 大仓:ZC 微仓:WC
  t.is_lian_suo_dian,
  t.province, -- 省
  t.city -- 城市
FROM master_warehouse t;


-- 原料详情
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

-- 原料周转天数
SELECT
  materials_id, -- 原料id
  turnover_days -- 周转天数
FROM master_materials;


-- 大仓系数
SELECT
  t.warehouse, -- 大仓编码
  t.proportion -- 系数
FROM psm_buhuo_para t
WHERE warehouse NOT like '%-%' AND type = 1;

-- 微仓系数
SELECT
  t.warehouse, -- 微仓编码
  t.proportion -- 系数
FROM psm_buhuo_para t
WHERE warehouse like '%-%' AND type = 1;


-- 微仓七日平均销量
SELECT
  t.warehouse, -- 微仓编号
  avg(t.qty) -- 平均销量
FROM psm_riqi_cangku_xiaoliang t
WHERE batch >= date_sub(curdate(), INTERVAL 7 DAY)
      AND batch < curdate()
      AND warehouse LIKE '%-%'
GROUP BY warehouse;

-- 明日星期x，取4个星期的平均销量
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
GROUP BY warehouse;


-- 黑名单
SELECT
  t.material_id, -- 原料id
  t.warehouse_id, -- 微仓编号
  t.value -- 是否黑名单
FROM psm_rule_map t
WHERE t.type = 'buhuoHeimingdan' AND del_flag = FALSE;

-- 黑名单
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
WHERE t.type = 'buhuoHeimingdan' AND del_flag = FALSE;



-- 新明日占比
-- 微仓前4个周X的品类平均
SELECT
  warehouse_code,
  category,
  AVG(qty) avg_qty
FROM
  psm_riqi_cangku_pinlei_xiaoliang t
WHERE warehouse_code like '%-%' AND  batch IN (
  date_sub(curdate(), INTERVAL 7 - 1 DAY),
  date_sub(curdate(), INTERVAL 2 * 7 -1 DAY),
  date_sub(curdate(), INTERVAL 3 * 7 -1 DAY),
  date_sub(curdate(), INTERVAL 4 * 7 -1 DAY)
)
GROUP BY warehouse_code,category
ORDER BY warehouse_code,category;

-- 今日销量
SELECT
  t.batch, -- 日期
  t.warehouse, -- 微仓编号
  t.material_id, -- 原料id
  t.sales_data -- 销售量
FROM psm_sales_data t
WHERE batch = curdate();


-- sku 规格数量
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
  b.qty DESC;


-- 大规格
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
WHERE t.type = 'daGuigeBuhuo' AND del_flag = FALSE;


# 最大补货数量
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
WHERE t.type = 'zuidaBuhuoShuliang' AND del_flag = FALSE;


-- 七日平均销量
SELECT
  warehouse, -- 微仓编号
  material_id, -- 原料id
  CAST(avg(sales_data) AS SIGNED) -- 销售量
FROM psm_sales_data
WHERE batch >= date_sub(curdate(), INTERVAL 7 DAY) AND batch < curdate()
GROUP BY warehouse, material_id;


-- 七日最高销量
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


-- 手工指定原料级别
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
WHERE type = 'yuanliaoJibie' AND del_flag = FALSE;

-- 品类系数
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
WHERE type = 'buhuoPinleiXishu' AND del_flag = FALSE;