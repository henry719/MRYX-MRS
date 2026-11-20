#!/usr/bin/env python
# -*- coding:utf-8 -*- 
"""
一个python文件
"""
import os
import logging
import logging.handlers
import traceback
import unittest

import math

__author__ = 'dongsibei'

logger = logging.getLogger(__name__)  # 默认日志


class COL(object):
    WAREHOUSE_ID = "warehouseId"
    WAREHOUSE_LIVE = "warehouseLive"
    BENFU_WAIFU = "benfuWaifu"
    CITY = "city"
    DAQU = "daqu"
    MATERIAL_ID = "materialId"
    MATERIAL_SHELFLIFE = "materialShelflife"
    STORE_CONDITION = "storeCondition"
    CATEGORY_ID = "categoryId"
    BCH2 = "bch2"


class ConstantsMongo(object):
    RULE_MAP = "ruleMap"
    FEI_NAI_CHU_YUAN_LIAO = "feiNaiChuYuanLiao"
    DA_GUIGE_BUHUO = "daGuigeBuhuo"
    ZUIDA_BUHUO_SHULIANG = "zuidaBuhuoShuliang"
    YUANLIAO_ZHOUZHUANTIANSHU = "yuanliaoZhouzhuantianshu"
    BUHUO_PICI = "buhuoPici"
    QINGSHI = "qingshi"
    FENPEI_YUANZHE = "fenpeiYuanzhe"
    DANLIANG_FENKUCUN = "danliangFenkucun"
    QINGSHI_SHOUQING_XISHU = "qingshiShouqingXishu"
    BUHUO_HEIMINGDAN = "buhuoHeimingdan"
    BAOCAI_DAGUIGEBUHUO = "baoCaiDaGuigeBuhuo"
    BAOCAI_FENPEIYUANZHE = "baoCaiFenpeiYuanzhe"
    BAOCAI_BUHUOAUTO = "baoCaiBuhuoAuto"
    BUHUO_PINLEI_XISHU = "buhuoPinleiXishu"
    BUHUO_ZHANDIAN_XISHU = "buhuoZhandianXishu"
    BUHUO_DAQU_XISHU = "buhuoDaquXishu"
    CAIGOU_JIANYI_CAIGOUXISHU = "caigouJianyiCaigouXishu"
    CIRIDA_KUCUN_YULIU = "ciridaKucunYuliu"
    KAOHE_ZHOUZHUANTIANSHU = "kaoheZhouzhuantianshu"
    CHANGDUANBAO = "changduanbao"
    BENFU_WAIFU = "benfuWaifu"
    YUANLIAO_JIBIE = "yuanliaoJibie"
    BUHUO_KURONG_LENGDONG = "buhuoKurongLengdong"
    BUHUO_KURONG_LENGCANG = "buhuoKurongLengcang"
    BUHUO_KURONG_BILI_LENGDONG = "buhuoKurongBiliLengdong"
    BUHUO_KURONG_BILI_LENGCANG = "buhuoKurongBiliLengcang"
    XIANGOUSHIDUAN_YUDINGMINGRI = "xiangoushiduanYudingmingri"
    pass


def makeMap(*args):
    d = {}
    for i in args:
        d[i] = True
    return d


class KeyMap(object):
    mapDefault = makeMap(COL.WAREHOUSE_ID, COL.WAREHOUSE_LIVE, COL.BENFU_WAIFU, COL.CITY, COL.DAQU, COL.MATERIAL_ID,
                         COL.MATERIAL_SHELFLIFE, COL.STORE_CONDITION, COL.CATEGORY_ID, COL.BCH2)
    mapChangduanbao = makeMap(COL.CATEGORY_ID)
    mapBenfuWaifu = makeMap(COL.WAREHOUSE_ID, COL.CITY)
    mapBuhuoHeimingdan = makeMap(COL.MATERIAL_ID, COL.STORE_CONDITION, COL.CATEGORY_ID, COL.WAREHOUSE_ID, COL.CITY,
                                 COL.DAQU)
    mapBuhuoPinleiXishu = makeMap(COL.STORE_CONDITION, COL.CATEGORY_ID, COL.WAREHOUSE_ID, COL.WAREHOUSE_LIVE, COL.CITY,
                                  COL.DAQU)
    mapYuanliaoZhouzhuantianshu = makeMap(COL.MATERIAL_ID, COL.WAREHOUSE_ID, COL.DAQU)
    mapBuhuoPici = makeMap(COL.MATERIAL_ID, COL.STORE_CONDITION, COL.CATEGORY_ID, COL.BCH2, COL.BENFU_WAIFU, COL.DAQU)
    mapYuanliaoJibie = makeMap(COL.MATERIAL_ID, COL.DAQU)
    mapBuhuoKurongLengdong = makeMap(COL.WAREHOUSE_ID)
    mapBuhuoKurongLengcang = makeMap(COL.WAREHOUSE_ID)
    mapBuhuoKurongLengdongBili = makeMap(COL.WAREHOUSE_ID)
    mapBuhuoKurongLengcangBili = makeMap(COL.WAREHOUSE_ID)
    mapDaGuigeBuhuo = makeMap(COL.MATERIAL_ID, COL.WAREHOUSE_ID, COL.WAREHOUSE_LIVE, COL.DAQU)
    mapZuidaBuhuoShuliang = makeMap(COL.MATERIAL_ID, COL.WAREHOUSE_ID, COL.DAQU)
    mapFenpeiYuanzhe = makeMap(COL.MATERIAL_ID, COL.DAQU)
    mapDanliangFenkucun = makeMap(COL.MATERIAL_ID, COL.DAQU)
    mapQingshiShouqingXishu = makeMap(COL.MATERIAL_ID, COL.DAQU)
    mapQingshi = makeMap(COL.MATERIAL_ID, COL.DAQU)
    mapBuhuoDaquXishu = makeMap(COL.STORE_CONDITION, COL.DAQU)
    mapBuhuoZhandianXishu = makeMap(COL.WAREHOUSE_ID)
    mapCaigouJianyiCaigouxishu = makeMap(COL.MATERIAL_ID, COL.STORE_CONDITION, COL.CATEGORY_ID, COL.DAQU)
    mapCiridaKucunYuliu = makeMap(COL.DAQU, COL.MATERIAL_ID)
    mapKaoheZhouzhuantianshu = makeMap(COL.CATEGORY_ID, COL.MATERIAL_SHELFLIFE)
    mapXiangoushiduanYudingmingri = makeMap(COL.BENFU_WAIFU, COL.DAQU)

    @staticmethod
    def getKeySetByRuleType(ruleType):
        if ruleType == ConstantsMongo.DA_GUIGE_BUHUO:
            return KeyMap.mapDaGuigeBuhuo
        if ruleType == ConstantsMongo.ZUIDA_BUHUO_SHULIANG:
            return KeyMap.mapZuidaBuhuoShuliang
        if ruleType == ConstantsMongo.FENPEI_YUANZHE:
            return KeyMap.mapFenpeiYuanzhe
        if ruleType == ConstantsMongo.DANLIANG_FENKUCUN:
            return KeyMap.mapDanliangFenkucun
        if ruleType == ConstantsMongo.QINGSHI_SHOUQING_XISHU:
            return KeyMap.mapQingshiShouqingXishu
        if ruleType == ConstantsMongo.QINGSHI:
            return KeyMap.mapQingshi
        if ruleType == ConstantsMongo.BUHUO_DAQU_XISHU:
            return KeyMap.mapBuhuoDaquXishu
        if ruleType == ConstantsMongo.BUHUO_ZHANDIAN_XISHU:
            return KeyMap.mapBuhuoZhandianXishu
        if ruleType == ConstantsMongo.CAIGOU_JIANYI_CAIGOUXISHU:
            return KeyMap.mapCaigouJianyiCaigouxishu
        if ruleType == ConstantsMongo.CIRIDA_KUCUN_YULIU:
            return KeyMap.mapCiridaKucunYuliu
        if ruleType == ConstantsMongo.KAOHE_ZHOUZHUANTIANSHU:
            return KeyMap.mapKaoheZhouzhuantianshu
        if ruleType == ConstantsMongo.XIANGOUSHIDUAN_YUDINGMINGRI:
            return KeyMap.mapXiangoushiduanYudingmingri
        if ruleType == ConstantsMongo.CHANGDUANBAO:
            return KeyMap.mapChangduanbao
        if ruleType == ConstantsMongo.BENFU_WAIFU:
            return KeyMap.mapBenfuWaifu
        if ruleType == ConstantsMongo.BUHUO_HEIMINGDAN:
            return KeyMap.mapBuhuoHeimingdan
        if ruleType == ConstantsMongo.BUHUO_PINLEI_XISHU:
            return KeyMap.mapBuhuoPinleiXishu
        if ruleType == ConstantsMongo.YUANLIAO_ZHOUZHUANTIANSHU:
            return KeyMap.mapYuanliaoZhouzhuantianshu
        if ruleType == ConstantsMongo.BUHUO_PICI:
            return KeyMap.mapBuhuoPici
        if ruleType == ConstantsMongo.YUANLIAO_JIBIE:
            return KeyMap.mapYuanliaoJibie
        if ruleType == ConstantsMongo.BUHUO_KURONG_LENGDONG:
            return KeyMap.mapBuhuoKurongLengdong
        if ruleType == ConstantsMongo.BUHUO_KURONG_LENGCANG:
            return KeyMap.mapBuhuoKurongLengcang
        if ruleType == ConstantsMongo.BUHUO_KURONG_BILI_LENGCANG:
            return KeyMap.mapBuhuoKurongLengcangBili
        if ruleType == ConstantsMongo.BUHUO_KURONG_BILI_LENGDONG:
            return KeyMap.mapBuhuoKurongLengdongBili
        return KeyMap.mapDefault

    pass


class RuleMapDto(object):
    def __init__(self):
        self.id = 0
        self.type = ''
        self.materialId = ''
        self.bch2 = ''
        self.materialShelflife = ''
        self.storeConditionCode = ''
        self.categoryId = ''
        self.warehouseId = ''
        self.warehouseLive = ''
        self.benfuWaifu = ''
        self.city = ''
        self.daqu = ''
        self.value = ''  # 规则值
        self.shelfLife = ''
        self.shelfLifeStart = ''
        self.shelfLifeEnd = ''
        self.createBy = ''
        self.createDate = ''
        self.createDateStart = ''
        self.createDateEnd = ''
        self.updateBy = ''
        self.updateDate = ''
        self.updateDateStart = ''
        self.updateDateEnd = ''
        self.remarks = ''
        self.delFlag = ''
        self.checked = ''
        self.materialName = ''
        self.warehouseName = ''
        self.appFlag = ''
        self.errMsg = ''

    @staticmethod
    def init(params):
        obj = RuleMapDto()
        obj.id, obj.type, obj.materialId, obj.bch2, obj.materialShelflife, \
        obj.storeConditionCode, obj.categoryId, obj.warehouseId, obj.warehouseLive, obj.benfuWaifu, \
        obj.city, obj.daqu, obj.value, obj.shelfLife, obj.createBy, \
        obj.createDate, obj.updateBy, obj.updateDate, obj.remarks, obj.delFlag = params
        return obj

    @staticmethod
    def createRuleMap(key, value):
        obj = RuleMapDto()
        obj.key = key
        obj.value = value
        return obj

    def getKey(self):
        ls = [
            self.warehouseId, self.warehouseLive, self.benfuWaifu, self.city,
            self.daqu, self.materialId, self.bch2, self.materialShelflife,
            self.storeConditionCode, self.categoryId
        ]
        return "[" + "]&[".join(map(str, ls)) + "]"

    def setKey(self, key):
        keys = key.split("&")
        values = [i[1:-1] for i in keys]
        self.warehouseId, self.warehouseLive, self.benfuWaifu, self.city, \
        self.daqu, self.materialId, self.bch2, self.materialShelflife, \
        self.storeConditionCode, self.categoryId = values


def getValueFromMapRuleCore(
        ruleType, warehouseId, warehouseLive, benfuWaifu, city, daqu, materialId, materialSelflife,
        storeCondition, category, bch2, mapRuleDict):
    """
    规则
    :param ruleType: 规则名称
    :param warehouseId:  微仓编码
    :param warehouseLive:
    :param benfuWaifu: 本阜外阜
    :param city: 城市
    :param daqu: 大仓编码
    :param materialId: 原料id
    :param materialSelflife: 保质期
    :param storeCondition: 温区
    :param category: 品类
    :param bch2: 波次2
    :param mapRuleDict: 规则数据
    :return:
    """
    # logger.info("正在解析规则[%s][%s][%s]", ruleType, materialId, warehouseId)
    mapKeyDict = KeyMap.getKeySetByRuleType(ruleType)
    paraCount = len(mapKeyDict)
    weightCount = int(math.pow(2, paraCount)) - 1

    dto = RuleMapDto()

    for i in range(weightCount, -1, -1):
        binaryString = str(bin(i)).replace('0b', '').zfill(paraCount)
        tmpInt = 0

        if COL.WAREHOUSE_ID in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.warehouseId = warehouseId
            else:
                dto.warehouseId = ''
            tmpInt += 1
        pass

        if COL.WAREHOUSE_LIVE in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.warehouseLive = warehouseLive
            else:
                dto.warehouseLive = ''
            tmpInt += 1
        pass

        if COL.BENFU_WAIFU in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.benfuWaifu = benfuWaifu
            else:
                dto.benfuWaifu = ''
            tmpInt += 1
        pass

        if COL.CITY in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.city = city
            else:
                dto.city = ''
            tmpInt += 1
        pass

        if COL.DAQU in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.daqu = warehouseId.split('-')[0]
            else:
                dto.daqu = ''
            tmpInt += 1
        pass

        if COL.MATERIAL_ID in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.materialId = materialId
            else:
                dto.materialId = ''
            tmpInt += 1
        pass

        if COL.BCH2 in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.bch2 = bch2
            else:
                dto.bch2 = ''
            tmpInt += 1
        pass

        if COL.MATERIAL_SHELFLIFE in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.materialShelflife = materialSelflife
            else:
                dto.materialShelflife = ''
            tmpInt += 1
        pass

        if COL.STORE_CONDITION in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.storeConditionCode = storeCondition
            else:
                dto.storeConditionCode = ''
            tmpInt += 1
        pass

        if COL.CATEGORY_ID in mapKeyDict:
            if "1" == binaryString[tmpInt:tmpInt + 1]:
                dto.categoryId = category
            else:
                dto.categoryId = ''
            tmpInt += 1
        pass

        if dto.getKey() in mapRuleDict and mapRuleDict[dto.getKey()].value != '':
            rule = mapRuleDict[dto.getKey()]
            return [rule.value, dto.getKey(), rule.remarks]
    return ['', '', '']


def main():
    logger.info('I am main')
    pass


# 主函数入口
if __name__ == '__main__':
    logger.debug('this is main.')
    try:
        main()
        xx
    except Exception as e:
        logger.exception('Exception Logged')
        pass
    logger.info('the main end.')


class MyTest(unittest.TestCase):
    # 初始化工作
    def setUp(self):
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
        pass

    # 清理工作
    def tearDown(self):
        pass

    # 语法测试变
    def test_hello(self):
        ls = ['a', 'b']
        try:
            print 'hello'
            print ls[3]
        except Exception as e:
            # info = sys.exc_info()
            # sys.stderr.write(str(info[0]) + ':' + str(info[1]))
            # print info[0],':',info[1]
            traceback.print_exc()
            raise ValueError('参数有错')
            # sys.stderr.write(traceback.format_exc())
            # info = sys.exc_info()
            # print(info)
            # msg = traceback.format_exc()
            # print(msg)
            pass
        pass
