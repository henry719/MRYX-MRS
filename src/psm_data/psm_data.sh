#!/usr/bin/env bash

#mysql -upsm -pdcnKXANtwo5dZUPL -h 10.10.120.27 -P 3306 -Dpsm -e "SELECT id, blg, value, create_time, create_user, update_time, update_user FROM psm.psm_holidays_config WHERE blg = '2018-05-29' AND value LIKE '\%休\%'" > holidays.txt

# 闭店日期: 日期 值
#python psm_data.py loadStopShopData > data/1/stop_shop.txt

# 大仓列表: 大仓编码 大仓名称 生存周期 城市名称
#python psm_data.py loadWhData > data/1/wh.txt

# 大仓原料7日销量: 大仓编码 原料id 平均销量
#python psm_data.py loadMidSale7Day > data/1/midsale_7day.txt

# 总销量,保留4位小数
#total_sale=$(cat data/1/midsale_7day.txt | awk -F '\t' '{sum += $3}END{printf("%.4f",sum)}')

# 计算原料等级: 大仓编码
#python psm_data.py doMidLevel ${total_sale} > data/1/mid_level.txt

# 原料两周内的最早售卖日期距离目前有几天: 大仓编码 原料id 相差天数
#python psm_data.py loadFirstSaleDay > data/1/sale_day.txt

# 今日已补数量: 微仓编码 原料id 已补数量
#python psm_data.py loadAlreadySupply > data/1/already_supply.txt

# 辅料: 商品sku 原料id
#python psm_data.py loadSubMid > data/1/sub_mid.txt

# 两天内微仓订单量: 微仓编码 订单数量
#python psm_data.py loadVcOrder > data/1/vc_order.txt

# 微仓七日品类订单量: 微仓(大仓)编码 品类 订单量
#python psm_data.py loadVcCateOrder > data/1/vc_cate_order.txt

# 微仓7日平均单量: 微仓编号 订单量
#python psm_data.py loadVcOrder_7DayAvg > data/1/vc_order_7dayavg.txt

# 总销量,保留4位小数
#total=$(cat data/1/vc_order_7dayavg.txt | awk -F '\t' '{sum += $2}END{printf("%.4f",sum)}')

# 微仓站点等级: 微仓编号 等级
#python psm_data.py doVcLevel ${total} > data/1/vc_level.txt

# 新品促销品: 大仓编码 城市 原料id 品类 原料名称 周转天数 温区 is_main, rebate, total_qty
#python psm_data.py loadNewsAndPromo | sort > data/1/new_promo.txt

# 干仓预留配置: 大仓编码 ip 端口
#python psm_data.py loadReserveInvConf > data/1/reserve_inv_conf.txt

# 干仓预留: 大仓编码 原料id 预留库存
#python psm_data.py doReserveInv > data/1/reserve_inv.txt

# 核心算法微仓应有数据:
#python psm_data.py loadAlgoData | sort > data/1/algo_shouldbe.txt

# 加载活动微仓,待补货的微仓(有售卖才有补货动作): 微仓编码 城市 微仓名称
# 此数据将作为补货的基础数据
#python psm_data.py loadActiveVc > data/1/active_vc.txt

# 微仓 本阜、外阜: 微仓编码 城市名称 微仓名称 本阜、外阜标记 订单量
#python psm_data.py loadVcLocalOuter | sort > data/1/vc_local_outer.txt

# 微仓外阜标记 : 微仓编码 外阜标记
#python psm_data.py loadVcOuter > data/1/vc_outer.txt

# 外阜比例: 大仓编码 外阜比例
#python psm_data.py doWhOuterRatio > data/1/wh_outer_ratio.txt

# 微仓 本阜、外阜 品类 销量: 微仓编码 城市名称 微仓名称 本阜、外阜标记 订单量 品类 销量
#python psm_data.py loadVcLocalOuterCate | sort > data/1/vc_local_outer_cate.txt

# 外阜品类销量比例: 大仓编码 品类 外阜比例
#python psm_data.py doWhOuterCateRatio | sort > data/1/wh_outer_cate_ratio.txt

# 在售原料列表: 大仓编码 原料id 品类 原料名称 周转天数 温区
#python psm_data.py loadOnlineMid | sort > data/1/online_mid.txt
# 追加新品促销品后的在售列表 : # 大仓编码 微仓编码 原料id 品类 原料名称 周转天数 温区
#python psm_data.py doOnlineMid > data/1/vc_online_mid.txt

# 补货批次
#python psm_data.py loadBatchHourConf | sort > data/1/batch_conf.txt
# 批次字典
#python psm_data.py doBatchDict  > data/1/batch_dict_json.txt

# 微仓详情: 仓库编号 仓库名称 warehouse_live 仓库类型 连锁店 省名称 城市名称
#python psm_data.py loadVcInfo > data/1/vc_info.txt

# 原料详情: 原料id 原料名称 品类id 存储温区 一级品类名称 保质期 单位 标记 是否短保 是否标品 保质期小时
#python psm_data.py loadMidInfo > data/1/mid_info.txt

# 原料周转天数：原料id 周转天数
#python psm_data.py loadMidTurnover > data/1/mid_turnover.txt

# 原料周转配置: 原料id 大仓编码 周转天数
#python psm_data.py loadMidTurnoverConf > data/1/mid_turnover_conf.txt
# 原料周转天数系数
#python psm_data.py doMidTurnOver > data/1/mid_turnover_rule.txt

# 微仓外阜标记: 微仓编码 城市名称 外阜标记(BF:本阜,WF:外阜)
#python psm_data.py loadVcOuterConf > data/1/vc_outer_conf.txt

# 微仓补货批次: 微仓编号 批次时间
#python psm_data.py loadVcBatchInfo > data/1/vc_batch.txt

# 批次数据输出 补货的基础数据
#python psm_data.py doBatch > data/1/batch.txt

# 大仓系数: 大仓编码 系数
#python psm_data.py loadWhParam > data/1/wh_param.txt

# 微仓系数: 微仓编码 系数
#python psm_data.py loadVcParam > data/1/vc_param.txt

# 微仓七日平均: 微仓编号 平均销量
#python psm_data.py loadVcWeekSale > data/1/vc_week_sale.txt

# 微仓明日星期平均销量: 微仓编号 平均销量
#python psm_data.py loadVcTomorowWeekSale > data/1/vc_tommorow_week_sale.txt

# 微仓明日占比 : 微仓编号 占比
#python psm_data.py doTomorowRatio > data/1/vc_tomorrow_ratio.txt

# 黑名单配置
#python psm_data.py loadBlackMidConf > data/1/black_mid_conf.txt
# 黑名单 : 大仓编码 微仓编码 原料id 标记
#python psm_data.py doBlackMid > data/1/black_mid.txt

# 微仓前四个周X的平均值 : 微仓编码 品类 平均值
#python psm_data.py loadVcCateWeekAvg > data/1/vc_cate_weekavg.txt
# 微仓30天4周 品类周平均 ：微仓编号 品类 均值
#python psm_data.py loadVcCate30DayWeekMean > data/1/vc_cate_30day_weekavg.txt
# 新明日占比 微仓品类明日占比: 微仓编号 品类 比例
#python psm_data.py doVcCateTomrrowRatio > data/1/vc_cate_tomorrow_tatio.txt

# 今日销量: 微仓编号 销量
#python psm_data.py loadTodaySale > data/1/today_sale.txt

# 原料规格 : 大仓编码 原料id 规格
#python psm_data.py loadMidUnit | sort | uniq > data/1/mid_unit.txt

# 大规格
#python psm_data.py loadBigUnitConf > data/1/big_unit_conf.txt
# 计算大规格 : 大仓编码 微仓编码 原料ID 大规格
#python psm_data.py doVcMidBigUnit > data/1/vc_mid_big_unit.txt

# 追加批次数据大规格
#python psm_data.py doBatchBigUnit > data/1/batch_bigUint.txt

# 微仓原料数据整理
#python psm_data.py doVcInvCollect > data/1/vc_mid_collect.txt
# 大仓原料数据整理
#python psm_data.py doWhInvCollect > data/1/wh_mid_collect.txt
# 获取库存
#java -Dloader.path=lib/ -Dspring.profiles.active=prod -jar atp-inv.jar wayaya

# 最大补货数量配置
#python psm_data.py loadMaxSupplyConf > data/1/max_supply_conf.txt
# 最大补货数量 : 大仓编码 微仓编码 原料id 最大值
#python psm_data.py doMaxSupply > data/1/vc_mid_max_supply.txt

# 追加最大补货数量
#python psm_data.py doBatchMaxSupply > data/1/batch_maxSupply.txt

# 七日平均销量: 微仓编码 原料id 平均销量
#python psm_data.py loadMidWeekMean > data/1/mid_weekmean.txt

# 七日最高销量 : 微仓编码 原料id 最高销量
#python psm_data.py loadMidMaxSale > data/1/mid_maxsale.txt

# 手工指定原料级别
#python psm_data.py loadMidLevelConf > data/1/mid_level_conf.txt

# 计算手动配置原料级别
#python psm_data.py doVcMidLevel > data/1/vc_mid_level.txt

# 品类系数配置
#python psm_data.py loadCateParamConf > data/1/cate_param_conf.txt
# 计算品类系数
#python psm_data.py doCateParam > data/1/cate_param.txt


# 今日还能销量 =  七日平均销量 - 今日销量
#python psm_data.py doTodayAbleSale > data/1/today_ablesale.txt

# 应补数量 = 应有数量 - 现有库存 + 今日还能销量
#python psm_data.py doShouldSupply 1> data/1/should_supply.txt  2>log.log


# 手工补货单
# 次日达预留库存
# 生成补货单

