SELECT
    norm_query,
    argMax(cpm_curr, version) AS cpm_curr,
    argMax(decision_time, version) AS decision_time
FROM default_db.bid_decision_log
WHERE adv_id = {adv_id:Int32}
  AND nmid IN {nmids:Array(UInt64)}
  AND norm_query IN {norm_queries:Array(String)}
GROUP BY adv_id, norm_query
