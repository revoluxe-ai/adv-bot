SELECT DISTINCT adv_id, norm_query
FROM default_db.clusters_adv_stats
WHERE adv_id IN {adv_ids:Array(UInt32)}
