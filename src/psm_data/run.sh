#!/usr/bin/env bash
set -e

function log(){
    echo $(date +'%Y-%m-%d %H:%M:%S') msg: $1
}

data_path=data/1
if [ ! -d ${data_path} ];then
    mkdir -p ${data_path}
fi

log 'start...'

log '待补货微仓...'
# 需要补货的微仓列表 : 微仓编码 城市 微仓名称
python psm_data.py loadActiveVc > data/1/active_vc.txt

log '活动的大仓列表...'
# 大仓编码
cat data/1/active_vc.txt | cut -d - -f1 | sort | uniq > data/1/active_wh.txt

log '大仓在售列表...'
# 在售原料列表: 大仓编码 原料id
python psm_data.py loadOnlineMid | sort > data/1/online_mid.txt

log '新品促销品'
# 新品促销品: 大仓编码 城市 原料id 品类 原料名称 周转天数 温区 is_main, rebate, total_qty
python psm_data.py loadNewsAndPromo | sort > data/1/new_promo.txt

# 追加新品促销品后的在售列表 : # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
#python psm_data.py doOnlineMid > data/1/vc_online_mid.txt

#log '数据部数据...'
# 数据部微仓应有: 微仓编码 原料id 应有数量
#python psm_data.py loadAlgoData | sort > data/1/algo_shouldbe.txt

#log '今日还能销量...'
# 今日还能销量 =  七日平均销量 - 今日销量 : 微仓编码 原料id 销量
#python psm_data.py doTodayAbleSale > data/1/today_ablesale.txt

#log '黑名单...'
# 黑名单配置
#python psm_data.py loadBlackMidConf > data/1/black_mid_conf.txt
# 黑名单 : 大仓编码 微仓编码 原料id 标记
#python psm_data.py doBlackMid > data/1/black_mid.txt

# 过滤黑名单


#log '现有库存'
# 微仓库存、大仓库存
# 微仓原料数据整理
#python psm_data.py doVcInvCollect > data/1/vc_mid_collect.txt
# 大仓原料数据整理
#python psm_data.py doWhInvCollect > data/1/wh_mid_collect.txt
# 获取库存
#java -Dloader.path=lib/ -Dspring.profiles.active=prod -jar atp-inv.jar wayaya 2>&1 > inv.log

#log '应补数量...'
# 应补数量 = 应有数量 - 现有库存 + 今日还能销量
#python psm_data.py doShouldSupply 1>data/1/should_supply.txt 2>error.log

# 强制补货

#log '过滤最大补货数量'...
#python psm_data.py filterMaxSupply >data/1/fileter_maxsupply_should_supply.txt

# 平均分配
#python psm_data.py allocation  > data/1/allocation.txt

# 库容
# python xx.py

# 辅料
# python xx.py


log 'end ...'
