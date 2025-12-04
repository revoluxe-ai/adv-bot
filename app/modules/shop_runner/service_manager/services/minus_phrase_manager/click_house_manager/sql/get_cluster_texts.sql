

SELECT DISTINCT norm_query
    FROM
        default_db.clusters_adv_stats
            WHERE adv_id = {adv_id: UInt32}