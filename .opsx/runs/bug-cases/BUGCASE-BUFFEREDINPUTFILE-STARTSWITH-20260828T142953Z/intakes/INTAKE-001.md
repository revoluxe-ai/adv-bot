INTAKE_RECORD

CASE_ID: BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z
INTAKE_ID: INTAKE-001
CREATED_AT: 2026-08-28T14:29:53.705938+00:00
SOURCE_TYPE: manual
SOURCE_REFERENCE: USER_MESSAGE / invocation payload WEX/MATERIALIZER/8937b1bee0
RAW_INTAKE_HASH: 0f7760309eaed24b5dde1232edacab6a7dc324fea762c7f8603fd38d60385069
RAW_INTAKE_SOURCE: USER_MESSAGE
RAW_INTAKE_RECEIVED_AT: 2026-08-28T14:29:53.705938+00:00

RAW_REPORT:
[28.08.2026 16:58] WB-Sky — раскрутка карточек WB через внутреннюю рекламу: /lib/python3.11/site-packages/aiogram/dispatcher/middlewares/user_context.py", line 27, in __call__
    return await handler(event, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/fsm/middleware.py", line 41, in __call__
    return await handler(event, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/client_bot/middlewars/immediate_callback_answer.py", line 82, in __call__
    return await handler(event, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/event/telegram.py", line 121, in trigger
    return await wrapped_inner(event, kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/event/handler.py", line 43, in call
    return await wrapped()
           ^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/dispatcher.py", line 276, in _listen_update
    return await self.propagate_event(update_type=update_type, event=event, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 128, in propagate_event
    return await observer.wrap_outer_middleware(_wrapped, event=event, data=kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 123, in _wrapped
    return await self._propagate_event(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 156, in _propagate_event
    response = await router.propagate_event(update_type=update_type, event=event, **kwargs)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 128, in propagate_event
    return await observer.wrap_outer_middleware(_wrapped, event=event, data=kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/fsm/scene.py", line 749, in _middleware
    return await handler(event, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 123, in _wrapped
    return await self._propagate_event(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 156, in _propagate_event
    response = await router.propagate_event(update_type=update_type, event=event, **kwargs)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 128, in propagate_event
    return await observer.wrap_outer_middleware(_wrapped, event=event, data=kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 123, in _wrapped
    return await self._propagate_event(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 156, in _propagate_event
    response = await router.propagate_event(update_type=update_type, event=event, **kwargs)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 128, in propagate_event
    return await observer.wrap_outer_middleware(_wrapped, event=event, data=kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/router.py", line 123, in _wrapped
    return await self._propagate_event(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispa
[28.08.2026 16:58] WB-Sky — раскрутка карточек WB через внутреннюю рекламу: tcher/router.py", line 148, in _propagate_event
    response = await observer.trigger(event, **kwargs)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/event/telegram.py", line 121, in trigger
    return await wrapped_inner(event, kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/client_bot/middlewars/phone_required.py", line 80, in __call__
    return await handler(event, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/client_bot/middlewars/channel_subscription.py", line 351, in __call__
    return await handler(event, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/client_bot/middlewars/gate.py", line 146, in __call__
    return await handler(event, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/modules/user_message_sender/middleware_for_adding_task.py", line 22, in __call__
    await handler(event, data)
  File "/app/.venv/lib/python3.11/site-packages/aiogram/dispatcher/event/handler.py", line 43, in call
    return await wrapped()
           ^^^^^^^^^^^^^^^
  File "/app/app/client_bot/user_interface/handlers/keyword_settings.py", line 832, in setting_keywords_by_adv
    await messages.AdvKeywordsSetting(
  File "/app/.venv/lib/python3.11/site-packages/dependency_injector/wiring.py", line 1072, in _patched
    return await fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/client_bot/user_interface/views/messages/adv_keyword_messages/adv_keyword_messages.py", line 214, in __call__
    result = await super().__call__()
             ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/client_bot/user_interface/message_templates/templates.py", line 41, in wrapper
    self.image = await file_handler.get_telegram_image(request, self.bot)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/file_handler.py", line 21, in get_telegram_image
    result = await _get_telegram_file(image_path, bot)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/app/file_handler.py", line 93, in _get_telegram_file
    raise e
  File "/app/app/file_handler.py", line 59, in _get_telegram_file
    if image_path.startswith("http"):
       ^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'BufferedInputFile' object has no attribute 'startswith'

--- footer ---

Ник пользователя: sky_manager_1


OBSERVED_SYMPTOM: AttributeError: BufferedInputFile has no attribute startswith in app/file_handler.py:_get_telegram_file via AdvKeywordsSetting
KNOWN_CONTEXT: |
  USER_FOOTER_NICK: sky_manager_1
  Stack originates from AdvKeywordsSetting -> get_telegram_image -> _get_telegram_file
  calling image_path.startswith("http") when image_path is BufferedInputFile.

NORMALIZED_OBSERVATIONS:
  OBSERVED_BEHAVIOR: Runtime AttributeError when _get_telegram_file treats BufferedInputFile as a str and calls startswith("http") during AdvKeywordsSetting image render.
  EXPECTED_BEHAVIOR_CANDIDATE: Telegram image helper accepts BufferedInputFile (or other InputFile) without str.startswith; http URL branch only for string paths.
  AFFECTED_AREA_CANDIDATE: app/file_handler.py:_get_telegram_file; callers AdvKeywordsSetting / get_telegram_image; keyword_settings.setting_keywords_by_adv
  REPRODUCTION_INFORMATION: Open keyword settings UI path that renders AdvKeywordsSetting with image supplied as BufferedInputFile; observe AttributeError in logs.
  EVIDENCE_REFERENCES: intakes/_RAW_INTAKE_SEED.txt (verbatim RAW_REPORT); stack frames through file_handler.py:59.
  INFERRED_ASSUMPTIONS: image_path may already be BufferedInputFile from upstream template/file_handler path; not a confirmed production classification.
  UNRESOLVED_QUESTIONS: Which callers pass BufferedInputFile vs str/URL; whether other get_telegram_* helpers share the same branch.

INTAKE_SUFFICIENCY: SUFFICIENT_FOR_CLASSIFICATION

STATUS: linked_to_finding
LAST_ACTIVITY_AT: 2026-08-28T14:46:12Z
NEXT_ACTION: /opsx-classify-bug case=BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z intake=INTAKE-001 finding=FINDING-001 claim_token=CLAIM/BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z/FINDING-001/2026-08-28T14:46:12Z
DISPOSITION:
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID: FINDING-001
RESULT_PATH:
