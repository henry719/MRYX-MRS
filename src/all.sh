#!/usr/bin/env bash
# 应有库存预测
# sh all.sh 环境 计算日 历史天数
# sh all.sh test 20180501 28
# $1 系统环境: prod test dev
set -e  # 出错退出
#set -x  # 开启调试模式

function log(){
    echo $(date +'%Y-%m-%d %H:%M:%S') msg: $1
}


log 'start'

# 判断环境参数 默认test
if [ "$1" ];then
    sed -i "s/flag = '\w\+'/flag = '$1'/" conf.py
else
    sed -i "s/flag = '\w\+'/flag = 'test'/" conf.py
fi

# 判断计算日期 默认当天
if [[ "$2" && -n "$2" && "$2" -ne "" ]];then
    sed -i "s/run_day = '[0-9]\{8\}'/run_day = '$2'/" conf.py
else
    today=$(date +'%Y%m%d')
    echo ${today}
    sed -i "s/run_day = '[0-9]\{8\}'/run_day = '${today}'/" conf.py
fi

# 判断数据天数 默认28天
if [[ "$3" && -n "$3" ]];then
    sed -i "s/day_span = [0-9]\{1,3\}/day_span = $3/" conf.py
else
    sed -i "s/day_span = [0-9]\{1,3\}/day_span = 28/" conf.py
fi

log 'start read'
spark-submit --master local[10] read_wayaya.py
log 'end read'

log 'start pre_data'
spark-submit --master local[20]  pre_data.py
log 'end pre_data'

log 'start algo'
spark-submit --master local[20]  algo.py
log 'end algo'

log 'end'