-- 用于获取库存
use supply;


-- wh,vc,cid,mid,sl,mean,sd,median,sum(yb) as shoule_be,percentitle,q95,mul,coes,coe,dp

-- 按大仓原料 汇总应有量
DROP TABLE IF EXISTS wh_mid_collect;
CREATE TABLE wh_mid_collect AS
  SELECT
    wh,
    mid,
    sum(yb) AS shoule_be,
    dp
  FROM da.wh_material_info
  WHERE dp = '${hiveconf:date_str}'
  GROUP BY wh, mid, dp;


-- 按微仓原料 汇总应有量
DROP TABLE IF EXISTS vc_mid_collect;
CREATE TABLE vc_mid_collect AS
  SELECT
    vc,
    mid,
    sum(yb) AS shoule_be,
    dp
  FROM da.wh_material_info
  WHERE dp = '${hiveconf:date_str}'
  GROUP BY vc, mid, dp;
