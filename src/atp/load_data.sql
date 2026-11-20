USE supply;

DROP TABLE IF EXISTS vc_mid_inv;
CREATE TABLE vc_mid_inv (
  vc STRING COMMENT '微仓编号',
  mid STRING COMMENT '原料id',
  inv DOUBLE COMMENT '逻辑库存'
) ROW FORMAT delimited FIELDS TERMINATED BY '\t';
LOAD DATA LOCAL inpath 'data/2/vc_mid_inv.txt' INTO TABLE vc_mid_inv;

DROP TABLE IF EXISTS wh_mid_inv;
CREATE TABLE wh_mid_inv (
  wh STRING COMMENT '大仓编码',
  mid STRING COMMENT '原料id',
  inv DOUBLE COMMENT '逻辑库存'
)ROW FORMAT delimited FIELDS TERMINATED BY '\t';
LOAD DATA LOCAL inpath 'data/2/wh_mid_inv.txt' INTO TABLE wh_mid_inv;