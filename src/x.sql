SELECT
  t1.channel,
  t1.region,
  count(DISTINCT t1.user_id),
  t1.dt,
  count(DISTINCT t2.user_id)
FROM
  (SELECT
     channel,
     CASE
     WHEN channel LIKE '%hb%' OR channel LIKE '%HB%' OR channel LIKE '%hB%' OR channel LIKE '%Hb%'
       THEN '华北'
     WHEN channel LIKE '%hn%' OR channel LIKE '%HN%' OR channel LIKE '%hN%' OR channel LIKE '%Hn%'
       THEN '华南'
     WHEN channel LIKE '%hd%' OR channel LIKE '%HD%' OR channel LIKE '%hD%' OR channel LIKE '%Hd%'
       THEN '华东'
     ELSE '其他'
     END AS region,
     user_id,
     dt
   FROM ods_log.ods_log_eventlog
   WHERE dt = '2018-05-01' AND label = 'product_detail' AND eventid = 'view_product' AND user_id NOT LIKE '%-%'
  ) t1
  LEFT JOIN
  (SELECT
     channel,
     CASE
     WHEN channel LIKE '%hb%' OR channel LIKE '%HB%' OR channel LIKE '%hB%' OR channel LIKE '%Hb%'
       THEN '华北'
     WHEN channel LIKE '%hn%' OR channel LIKE '%HN%' OR channel LIKE '%hN%' OR channel LIKE '%Hn%'
       THEN '华南'
     WHEN channel LIKE '%hd%' OR channel LIKE '%HD%' OR channel LIKE '%hD%' OR channel LIKE '%Hd%'
       THEN '华东'
     ELSE '其他'
     END AS region,
     user_id,
     dt
   FROM ods_log.ods_log_eventlog
   WHERE dt = '2018-05-01' AND label = 'channel' AND eventid = 'product_show' AND user_id NOT LIKE '%-%'
  ) t2 ON t1.dt = t2.dt AND t1.channel = t2.channel
GROUP BY t1.channel, t1.dt, t1.region
