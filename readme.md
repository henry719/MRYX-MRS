### 供需补货
mrs(mini replenishment warehouse)

### 环境
服务器:10.10.47.31


### 运行
注意：运行前请查看配置，不要影响线上数据

准备数据
shell> spark-submit --master yarn pre_debug.py

算法执行
shell> spark-submit --master local[20] algo.py


获取所有大仓列表
server:10.10.131.156:3306
user:bi_u28 
password:ki*safsaHb-d

shell> mysql -h 10.10.131.156 -P 3306 -ubi_u28 -p'ki*safsaHb-d' -e "select DISTINCT daqu from bi_bak.shj_yuanliao_xiaoshou_infor_all_month where vc_batch='2018-05-18'"

mysql> select DISTINCT daqu from bi_bak.shj_yuanliao_xiaoshou_infor_all_month where vc_batch='2018-05-18'
MRYXSH
MRYXSZ
MRYXTJ


mysql> select DISTINCT substring_index(vc_warehouse,'-',1) from shj_yuanliao_xiaoshou_infor_all_month where vc_batch='2018-05-18';
MRYXSHW
MRYXSZ
MRYXBJN
MRYXTJ
MRYXNJ

shell> mysql -h 10.10.131.156 -P 3306 -ubi_28 -p'ki*safsaHb-d' -e "select DISTINCT substring_index(vc_warehouse,'-',1) from shj_yuanliao_xiaoshou_infor_all_month where vc_batch='2018-05-18'" >x.txt


### 连接PSM备库 readonly
host:10.10.120.27
port:3306
db:psm
user:data_use_r
pwd:jWQVAYD_EO-wTu6-

### 连接PSM线上主库
host:10.10.120.27 
port=3306
db=psm
user:psm
pwd:dcnKXANtwo5dZUPL
