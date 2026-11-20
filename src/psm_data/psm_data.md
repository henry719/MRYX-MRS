### ATP库存
http://wiki.missfresh.net/pages/viewpage.action?pageId=4915303#ATP%E6%8F%90%E4%BE%9B%E7%9A%84HTTP%E6%8E%A5%E5%8F%A3-1.1.getATP%E6%8E%A5%E5%8F%A3


获取大仓库存
curl -H "Content-Type: application/json" -X POST -d '{"warehouse":"MRYXTJ-WANGJING","outer_ids":["p-HBhnmg-1g"]}' http://172.16.30.79:18001/atp/getATP.json


1. 需要补货的微仓
2. 在售列表
