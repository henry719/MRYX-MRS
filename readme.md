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


