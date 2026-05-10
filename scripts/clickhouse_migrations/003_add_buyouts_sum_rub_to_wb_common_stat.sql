-- Сумма выкупов в рублях по дню/nmid (WB API buyoutsSumRub).
ALTER TABLE default_db.wb_common_stat
    ADD COLUMN IF NOT EXISTS buyouts_sum_rub Float64 DEFAULT 0 AFTER buy_outs;
