# Time and Date Retrieval Usage Report

## datetime.now
Found 78 occurrence(s):
- ./tools/time_usage_audit.py:6:    "datetime.now": r"datetime\.now",
- ./get_adv_spend_by_user.py:39:                    AdvKeyword.date == datetime.datetime.now().date(),
- ./examples/token_monitoring_demo.py:171:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)
- ./examples/token_monitoring_demo.py:178:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)
- ./examples/token_monitoring_demo.py:183:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=1)
- ./k8s/monitoring/error_monitor.py:130:                        timestamp=datetime.now().isoformat(),
- ./k8s/monitoring/error_monitor.py:168:                    timestamp=datetime.now().isoformat(),
- ./k8s/monitoring/error_monitor.py:211:                timestamp=datetime.now().isoformat(),
- ./k8s/monitoring/error_monitor.py:302:            "timestamp": datetime.now().isoformat(),
- ./get_clients_to_file.py:21:end_date = datetime.now().date()
- ./upload_full_adv_stat.py:27:    today = datetime.now().date()
- ./conftest.py:221:                    "expiration_time": datetime.now() + timedelta(days=7),
- ./tests/modules/shop_menu/test_shop_menu_add_token_button.py:63:    cabinet.expiration_time = datetime.now() + timedelta(days=30)
- ./tests/modules/shop_menu/test_shop_menu_token_loading.py:57:        wb_cabinet.expiration_time = datetime.datetime.now() + datetime.timedelta(
- ./tests/modules/shop_menu/test_shop_menu_token_loading.py:81:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/modules/shop_menu/test_token_loading_bug_reproduction.py:46:        wb_cabinet.expiration_time = datetime.datetime.now() + datetime.timedelta(
- ./tests/modules/shop_menu/test_token_loading_bug_reproduction.py:67:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/modules/shop_menu/test_simplified_token_display.py:62:            expires=expiration_date or datetime.now() + timedelta(days=30),
- ./tests/modules/shop_menu/test_simplified_token_display.py:89:        expiration_date = datetime.now() + timedelta(days=60)
- ./tests/modules/shop_menu/test_simplified_token_display.py:110:        expiration_date = datetime.now() + timedelta(days=2)
- ./tests/modules/shop_menu/test_simplified_token_display.py:127:        expiration_date = datetime.now() + timedelta(days=5)
- ./tests/modules/shop_menu/test_simplified_token_display.py:146:        expiration_date = datetime.now() + timedelta(days=15)
- ./tests/modules/shop_menu/test_simplified_token_display.py:223:            "Complete", set(), datetime.now() + timedelta(days=30)
- ./tests/modules/shop_menu/test_simplified_token_display.py:245:        expiration_date = datetime.now() + timedelta(days=365)
- ./tests/modules/shop_menu/test_process_tokens.py:60:        mock_token.expires = datetime.datetime.now() + datetime.timedelta(
- ./tests/modules/shop_menu/test_message_tariff.py:42:        wb_cabinet.expiration_time = datetime.now() + timedelta(days=30)
- ./tests/modules/modules/token_monitoring/test_token_monitoring.py:59:        wb_cabinet.expiration_time = datetime.datetime.now() + datetime.timedelta(
- ./tests/modules/modules/token_monitoring/test_token_monitoring.py:83:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/modules/modules/token_monitoring/test_token_monitoring.py:105:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/modules/modules/token_monitoring/test_token_monitoring.py:131:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=3)
- ./tests/modules/wb_adv_updater/position_history_manager/test_position_history_manager.py:49:    now = datetime.now()
- ./tests/manual_test_runner.py:176:    mock_wb_cabinet.expiration_time = datetime.now() + timedelta(days=30)
- ./tests/token_monitoring/test_notification_manager.py:97:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)
- ./tests/token_monitoring/test_notification_manager.py:124:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)
- ./tests/token_monitoring/test_notification_manager.py:149:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=1)
- ./tests/token_monitoring/test_notification_manager.py:337:            expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)
- ./tests/token_monitoring/test_notification_manager.py:356:            expiry_date = datetime.datetime.now() + datetime.timedelta(days=5)
- ./tests/token_monitoring/test_scheduler.py:127:            mock_datetime.now.return_value = mock_now
- ./tests/token_monitoring/test_scheduler.py:158:            mock_datetime.now.return_value = mock_now
- ./tests/token_monitoring/test_scheduler.py:185:            mock_datetime.now.side_effect = Exception("Time calculation error")
- ./tests/token_monitoring/test_scheduler.py:236:            mock_datetime.now.return_value = mock_now
- ./tests/token_monitoring/test_scheduler.py:262:            mock_datetime.now.return_value = mock_now
- ./tests/token_monitoring/test_integration.py:202:        valid_token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/token_monitoring/test_integration.py:212:        expired_token.expires = datetime.datetime.now() - datetime.timedelta(days=1)
- ./tests/modules/token_monitoring/test_property_query_bug.py:87:        cutoff_date = datetime.datetime.now() + datetime.timedelta(days=14)
- ./tests/modules/token_monitoring/test_property_query_bug.py:135:            now = datetime.datetime.now()
- ./tests/token_monitoring/test_token_info_service.py:36:        token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/token_monitoring/test_token_info_service.py:50:        token.expires = datetime.datetime.now() - datetime.timedelta(days=1)
- ./tests/token_monitoring/test_token_info_service.py:122:        incomplete_token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/token_monitoring/test_token_info_service.py:173:        limited_token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/token_monitoring/test_token_info_service.py:225:            expires=datetime.datetime.now() + datetime.timedelta(days=5),
- ./tests/token_monitoring/test_token_info_service.py:258:            expires=datetime.datetime.now() + datetime.timedelta(days=30),
- ./tests/token_monitoring/test_token_info_service.py:270:            expires=datetime.datetime.now() - datetime.timedelta(days=1),
- ./tests/modules/token_monitoring/test_improved_token_status.py:32:            expires=datetime.datetime.now() + datetime.timedelta(days=30),
- ./tests/modules/token_monitoring/test_improved_token_status.py:44:            expires=datetime.datetime.now()
- ./tests/modules/token_monitoring/test_improved_token_status.py:80:            expires=datetime.datetime.now() + datetime.timedelta(days=30),
- ./tests/modules/token_monitoring/test_improved_token_status.py:115:            expires=datetime.datetime.now() + datetime.timedelta(days=5),
- ./tests/modules/token_monitoring/test_improved_token_status.py:128:            expires=datetime.datetime.now()
- ./tests/modules/token_monitoring/test_improved_token_status.py:170:            expires=datetime.datetime.now()
- ./tests/modules/token_monitoring/test_improved_token_status.py:203:            expires=datetime.datetime.now() + datetime.timedelta(days=30),
- ./tests/modules/token_monitoring/test_improved_token_status.py:237:        same_date = datetime.datetime.now() + datetime.timedelta(days=7)
- ./tests/token_monitoring/test_token_expiration_service.py:53:        now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
- ./tests/token_monitoring/test_models.py:35:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)
- ./tests/integration/test_full_wb_adv_stat.py:179:        expiration_time=dt.datetime.now() + dt.timedelta(days=7),
- ./tests/wb_token_mock.py:15:                (datetime.datetime.now() + datetime.timedelta(days=30)).timestamp()
- ./tests/test_wb_shop_coroutines.py:132:    now_dt = datetime.now(timezone.utc)
- ./tests/test_get_days_stat.py:29:    test_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
- ./tests/factories/complex_adv.py:177:            cluster_stat__timestamp=datetime.now(),
- ./tests/factories/keyword_position_factory.py:15:            datetime.now(timezone.utc) - timedelta(days=30),
- ./tests/factories/keyword_position_factory.py:16:            datetime.now(timezone.utc)
- ./app/modules/wb_adv_updater/data_manager.py:175:#         start_time = datetime.now() - pass_time
- ./app/modules/wb_adv_updater/data_manager.py:242:#         update = datetime.now() - timedelta(days=1000)
- ./app/modules/wb_adv_updater/data_manager.py:841:#         return int(datetime.now().timestamp())
- ./app/modules/shop_runner/service_manager/services/keyword_stamp_manager/keyword_stamp_manager.py:101:                timestamp=datetime.now(ZoneInfo("Europe/Moscow")),
- ./app/utils/timezone.py:10:    return datetime.datetime.now(MOSCOW_TZ)
- ./app/utils/redis_manager/__init__.py:93:    # now = datetime.datetime.now()
- ./app/utils/redis_manager/__init__.py:174:#         position.timestamp = datetime.datetime.now()
- ./app/core/redis_manager_v2/mixins/wb_positions.py:13:    #         position.timestamp = datetime.now()

## datetime.utcnow
Found 6 occurrence(s):
- ./tools/time_usage_audit.py:7:    "datetime.utcnow": r"datetime\.utcnow",
- ./tests/factories/clickhouse_factory.py:41:    timestamp = factory.LazyFunction(datetime.utcnow)
- ./tests/token_monitoring/test_models.py:21:            sent_at=datetime.datetime.utcnow(),
- ./tests/token_monitoring/test_models.py:42:            sent_at=datetime.datetime.utcnow(),
- ./tests/token_monitoring/test_models.py:57:            sent_at=datetime.datetime.utcnow(),
- ./tests/token_monitoring/test_models.py:70:        sent_at = datetime.datetime.utcnow()

## datetime.today
Found 1 occurrence(s):
- ./tools/time_usage_audit.py:8:    "datetime.today": r"datetime\.today",

## date.today
Found 13 occurrence(s):
- ./tools/time_usage_audit.py:9:    "date.today": r"date\.today",
- ./tests/test_sqlalchemy_models_initialization.py:128:            adv_payment = AdvPayment(date=date.today(), adv_setting_id=1)  # type: ignore[no-untyped-call]
- ./tests/test_sqlalchemy_models_initialization.py:129:            assert adv_payment.date == date.today()
- ./tests/modules/wb_adv_updater/position_history_manager/test_position_history_manager.py:47:    today = date.today()
- ./tests/modules/shop_runner/service_manager/services/keyword_stamp_manager/click_house_manager/test_clickhouse_keyword_stamp_manager.py:126:    today = date.today()
- ./tests/app/core/mp/wb/api/adapter/promotion_client/normquery_stats/test_normquery_stats_adapter.py:57:    today = datetime.date.today()
- ./tests/app/core/mp/wb/api/domain_managers/promotion/test_promotion_manager.py:32:    today = datetime.date.today()
- ./tests/test_wb_shop_coroutines.py:130:    base_date = date.today()
- ./tests/factories/clickhouse_factory.py:40:    date = factory.LazyFunction(date.today)
- ./tests/utils/test_graphic_positions_creator.py:28:    today = datetime.date.today()
- ./tests/utils/test_graphic_positions_creator.py:160:        today = datetime.date.today()
- ./tests/utils/test_graphic_positions_creator.py:204:        today = datetime.date.today()
- ./tests/utils/test_graphic_positions_creator.py:222:        today = datetime.date.today()

## time.time
Found 85 occurrence(s):
- ./tools/time_usage_audit.py:10:    "time.time": r"time\.time",
- ./examples/token_monitoring_demo.py:171:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)
- ./examples/token_monitoring_demo.py:178:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)
- ./examples/token_monitoring_demo.py:183:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=1)
- ./tests/modules/shop_menu/test_shop_menu_token_loading.py:57:        wb_cabinet.expiration_time = datetime.datetime.now() + datetime.timedelta(
- ./tests/modules/shop_menu/test_shop_menu_token_loading.py:81:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/modules/shop_menu/test_token_loading_bug_reproduction.py:46:        wb_cabinet.expiration_time = datetime.datetime.now() + datetime.timedelta(
- ./tests/modules/shop_menu/test_token_loading_bug_reproduction.py:67:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/modules/shop_menu/test_process_tokens.py:60:        mock_token.expires = datetime.datetime.now() + datetime.timedelta(
- ./tests/modules/modules/token_monitoring/test_token_monitoring.py:59:        wb_cabinet.expiration_time = datetime.datetime.now() + datetime.timedelta(
- ./tests/modules/modules/token_monitoring/test_token_monitoring.py:83:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/modules/modules/token_monitoring/test_token_monitoring.py:105:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/modules/modules/token_monitoring/test_token_monitoring.py:131:        token_info.expires = datetime.datetime.now() + datetime.timedelta(days=3)
- ./app/modules/wb_adv_updater/fitter.py:77:#     start_time = time.time()
- ./app/modules/wb_adv_updater/fitter.py:194:#     execution_time = time.time() - start_time
- ./app/modules/wb_adv_updater/wb_manager.py:392:    _period = datetime.timedelta(minutes=10)
- ./tests/modules/token_monitoring/test_property_query_bug.py:87:        cutoff_date = datetime.datetime.now() + datetime.timedelta(days=14)
- ./tests/modules/token_monitoring/test_property_query_bug.py:143:            expiring_token.expires = now + datetime.timedelta(days=5)
- ./tests/modules/token_monitoring/test_property_query_bug.py:152:            future_token.expires = now + datetime.timedelta(days=30)
- ./tests/modules/token_monitoring/test_improved_token_status.py:32:            expires=datetime.datetime.now() + datetime.timedelta(days=30),
- ./tests/modules/token_monitoring/test_improved_token_status.py:45:            + datetime.timedelta(days=10),  # Earlier expiration
- ./tests/modules/token_monitoring/test_improved_token_status.py:80:            expires=datetime.datetime.now() + datetime.timedelta(days=30),
- ./tests/modules/token_monitoring/test_improved_token_status.py:115:            expires=datetime.datetime.now() + datetime.timedelta(days=5),
- ./tests/modules/token_monitoring/test_improved_token_status.py:129:            + datetime.timedelta(days=1),  # Earlier but irrelevant
- ./tests/modules/token_monitoring/test_improved_token_status.py:171:            + datetime.timedelta(hours=12),  # Less than 1 day
- ./tests/modules/token_monitoring/test_improved_token_status.py:203:            expires=datetime.datetime.now() + datetime.timedelta(days=30),
- ./tests/modules/token_monitoring/test_improved_token_status.py:237:        same_date = datetime.datetime.now() + datetime.timedelta(days=7)
- ./tests/wb_token_mock.py:15:                (datetime.datetime.now() + datetime.timedelta(days=30)).timestamp()
- ./app/modules/common_slaves/wildberries/wb_api.py:128:        date_from = date_to - datetime.timedelta(days=6)
- ./app/modules/common_slaves/wildberries/api/api.py:209:        date_from = date_to - datetime.timedelta(days=6)
- ./tests/test_get_days_stat.py:29:    test_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
- ./tests/test_get_days_stat.py:48:    common_card_stat_mock.date = datetime.datetime.combine(test_date, datetime.time.min)
- ./tests/utils/test_graphic_positions_creator.py:35:            date = today - datetime.timedelta(days=days_ago)
- ./tests/utils/test_graphic_positions_creator.py:167:                date = today - datetime.timedelta(days=days_ago)
- ./tests/utils/test_graphic_positions_creator.py:207:            make_position("тест", today - datetime.timedelta(days=1), 5.0),
- ./tests/utils/test_graphic_positions_creator.py:208:            make_position("тест", today - datetime.timedelta(days=2), 15.0),
- ./tests/utils/test_graphic_positions_creator.py:225:            make_position("ключ_1", today - datetime.timedelta(days=1), 12.0),
- ./tests/utils/test_graphic_positions_creator.py:227:            make_position("ключ_2", today - datetime.timedelta(days=1), 7.0),
- ./tests/token_monitoring/test_notification_manager.py:97:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)
- ./tests/token_monitoring/test_notification_manager.py:124:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)
- ./tests/token_monitoring/test_notification_manager.py:149:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=1)
- ./tests/token_monitoring/test_notification_manager.py:337:            expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)
- ./tests/token_monitoring/test_notification_manager.py:356:            expiry_date = datetime.datetime.now() + datetime.timedelta(days=5)
- ./tests/token_monitoring/test_integration.py:144:        expiring_token.expires = fixed_now + datetime.timedelta(days=14)
- ./tests/token_monitoring/test_integration.py:202:        valid_token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/token_monitoring/test_integration.py:212:        expired_token.expires = datetime.datetime.now() - datetime.timedelta(days=1)
- ./tests/token_monitoring/test_integration.py:403:            token.expires = fixed_now + datetime.timedelta(days=days)
- ./tests/token_monitoring/test_token_info_service.py:36:        token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/token_monitoring/test_token_info_service.py:50:        token.expires = datetime.datetime.now() - datetime.timedelta(days=1)
- ./tests/token_monitoring/test_token_info_service.py:65:            reason="Failing due to AssertionError: assert datetime.datetime(2025, 11, 25, 22, 29, 54, 845615, tzinfo=datetime.timezone.utc) == datetime.datetime(2025, 11, 25, 2..."
- ./tests/token_monitoring/test_token_info_service.py:122:        incomplete_token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/token_monitoring/test_token_info_service.py:173:        limited_token.expires = datetime.datetime.now() + datetime.timedelta(days=30)
- ./tests/token_monitoring/test_token_info_service.py:225:            expires=datetime.datetime.now() + datetime.timedelta(days=5),
- ./tests/token_monitoring/test_token_info_service.py:258:            expires=datetime.datetime.now() + datetime.timedelta(days=30),
- ./tests/token_monitoring/test_token_info_service.py:270:            expires=datetime.datetime.now() - datetime.timedelta(days=1),
- ./tests/token_monitoring/test_token_expiration_service.py:54:        token.expires = now + datetime.timedelta(
- ./app/modules/shop_runner/service_manager/services/keyword_stamp_manager/click_house_manager.py:24:            version = str(time.time())
- ./tests/token_monitoring/test_models.py:35:        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)
- ./app/modules/shop_runner/service_manager/services/keyword_stamp_manager/click_house_manager/click_house_manager.py:35:        version = int(time.time() * 1000)
- ./app/modules/shop_runner/service_manager/services/keyword_stamp_manager/click_house_manager/click_house_manager.py:87:        version = int(time.time() * 1000)
- ./tests/app/modules/shop_runner/bidder/test_run_bidder_process_for_adv_redis_cache_integration.py:92:            expected_timestamp = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
- ./app/modules/user_message_sender/message_for_not_pay_user_sender.py:68:    now = time.time()
- ./app/modules/shop_runner/wb_stat_manager/clickhouse_manager/test_get_daily_stats_by_last_days.py:18:    yesterday = today - datetime.timedelta(days=1)
- ./app/modules/shop_runner/wb_stat_manager/clickhouse_manager/test_get_daily_stats_by_last_days.py:98:    yesterday = today - datetime.timedelta(days=1)
- ./app/modules/shop_runner/wb_stat_manager/clickhouse_manager/full_wb_adv_stat.py:238:        version = str(time.time())
- ./app/modules/shop_runner/bidder/redis_cache/last_keyword_stamp_timestamp_cache.py:24:        value_str = value.astimezone(datetime.timezone.utc).isoformat()
- ./app/core/wb_api/http_request.py:86:                    current_time = time.time()
- ./app/core/wb_api/http_request.py:94:                    state["_last_query_time"] = time.time()
- ./app/modules/shop_runner/wb_statistic_manager/backend/common_stat_manager.py:165:        version = time.time()
- ./app/modules/token_monitoring/services/token_info_service.py:323:        cutoff_date = now_moscow() + datetime.timedelta(days=days_ahead)
- ./app/modules/token_monitoring/services/token_expiration_service.py:175:        max_check_ahead = datetime.timedelta(days=max(self.WARNING_STAGES))
- ./app/modules/token_monitoring/services/token_expiration_service.py:216:            cutoff_date = now + datetime.timedelta(days=days_ahead)
- ./app/modules/token_monitoring/services/token_expiration_service.py:284:            cutoff_date = now_moscow() - datetime.timedelta(days=older_than_days)
- ./app/core/mp/wb/api/retry_decorator.py:66:                        current_time = time.time()
- ./app/core/mp/wb/api/retry_decorator.py:75:                        state["_last_query_time"] = time.time()
- ./app/core/mp/wb/api/retry_decorator.py:103:                        state["_last_query_time"] = time.time()
- ./app/core/mp/wb/api/retry_decorator.py:119:                        state["_last_query_time"] = time.time()
- ./app/utils/graphic_positions_creator/graphic_positions_creator.py:63:        start_date = end_date - datetime.timedelta(days=7)
- ./app/utils/redis_manager/__init__.py:94:    # expire = now + datetime.timedelta(seconds=timeout)
- ./app/utils/redis_manager/__init__.py:325:    value = block_position_status + ":" + str(new_time.timestamp())
- ./app/utils/redis_manager/__init__.py:706:    time_now = time.time()
- ./app/client_bot/user_interface/views/messages/adv_keyword_messages/backend/common_stat_data_manager.py:24:        start_date = end_date - datetime.timedelta(days=last_days)
- ./app/client_bot/user_interface/views/messages/adv_keyword_messages/backend/common_stat_data_manager.py:60:        start_date = end_date - datetime.timedelta(days=last_days)
- ./app/core/mp/wb/api/domain_managers/analytics/methods/get_keyword_positions.py:19:    from_date = today - datetime.timedelta(days=for_last_days - 1)
- ./app/core/redis_cache/mixins/data_types/pass_time_redis_cache_base.py:14:        if timestamp + datetime.timedelta(seconds=pass_time_sec) <= now:

## time.monotonic
Found 1 occurrence(s):
- ./tools/time_usage_audit.py:11:    "time.monotonic": r"time\.monotonic",

## time.perf_counter
Found 1 occurrence(s):
- ./tools/time_usage_audit.py:12:    "time.perf_counter": r"time\.perf_counter",
