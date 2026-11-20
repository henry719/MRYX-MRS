USE supply;

-- 保存 库存信息
DROP TABLE IF EXISTS wh_material_inv;
CREATE TABLE wh_material_inv AS
  SELECT
    a.*,
    b.inv AS vc_inv,
    c.inv AS wh_inv
  FROM da.wh_material_info a LEFT JOIN vc_mid_inv b ON a.vc = b.vc AND a.mid = b.mid
    LEFT JOIN wh_mid_inv c ON a.wh = c.wh AND a.mid = c.mid
  WHERE a.dp = '${hiveconf:date_str}'