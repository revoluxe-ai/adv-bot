-- anyLast(wb_category) for (adv_id, nmid) over last N days, non-empty.
SELECT anyLast(t.wb_category) AS wb_category
FROM default_db.bid_decision_log AS t
WHERE t.adv_id = {adv_id:Int32}
  AND t.nmid = {nmid:UInt64}
  AND t.wb_category != ''
  AND t.decision_time >= now() - toIntervalDay({window_days:UInt32})
