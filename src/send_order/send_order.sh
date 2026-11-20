#!/usr/bin/env bash
set -e

basedir=$(cd `dirname $0`;pwd)  # 获取当前路径
data_dir=data  # 数据目录

function log(){
    echo $(date +'%Y-%m-%d %H:%M:%S') msg: $1
}

# 删除多余的备份数据
function delbakData(){
    # 仅保留七天的备份
    path=$1
    cd ${path} # 切换目录
    arr=($(ls -t ${path} | grep data_))  # 获取备份数据列表
    files=${arr[@]:7}  # 获取大于7天的数据列表
    for file in ${files[*]};
    do
        rm -rf ${file}  # 删除多余的备份数据
    done
    cd -  # 返回上一个路径
}

# 创建数据目录
function createDataDir(){
    if [ -e data ];then
        mv data data_${date_str}  # 备份老数据
        log '删除备份数据'
        delbakData ${basedir}
    fi

    log '创建数据目录'
    mkdir -p ${data_dir}/0
    mkdir -p ${data_dir}/1
    mkdir -p ${data_dir}/2
}

log 'start'

date_str=$(date +'%Y%m%d')  # 当前日期

createDataDir

log '获取应补数据'
# 微仓编号 原料id 应补数量 日期
hive -e "select * from supply.wh_material_yb where dp='${date_str}' order by vc,mid" > data/1/wh_material_yb.txt

log 'end'