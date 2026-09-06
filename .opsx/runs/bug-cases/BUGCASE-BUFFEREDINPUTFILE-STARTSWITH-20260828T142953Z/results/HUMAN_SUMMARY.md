# Что произошло

При показе настроек ключевых слов рекламы (AdvKeywordsSetting) бот падал с AttributeError: у объекта BufferedInputFile нет метода startswith. Ошибка возникала в app/file_handler.py при подготовке картинки для Telegram.

# Что было сломано

Функция _get_telegram_file принимала и строковый путь/URL, и уже готовый BufferedInputFile, но сразу вызывала startswith("http") как у строки. Когда приходил BufferedInputFile, вызов падал.

# Почему это было проблемой

Падение ломало экран настроек ключевых слов: пользователь не мог открыть меню с картинкой/файлом. Это runtime-баг на реальном пути manage_file_id → get_telegram_image.

# Что мы изменили

В _get_telegram_file добавлен ранний isinstance(..., BufferedInputFile) passthrough: готовый BufferedInputFile возвращается как есть. startswith("http") вызывается только после сужения типа до str. Тип аргумента расширен до str | BytesIO | BufferedInputFile | None. Добавлены docstring'и.

# Какие файлы изменены

- app/file_handler.py
- tests/unit/test_file_handler_buffered_input_file.py

## Изменения этого bug episode

- app/file_handler.py
- tests/unit/test_file_handler_buffered_input_file.py

## Ранее существовавшие несвязанные изменения

- (нет)

# Как мы проверили

RED: два unit-теста падали на старом коде (AttributeError на startswith). После фикса GREEN: те же тесты (тот же TEST_CONTENT_SHA256) проходят. Bounded hunt CLEAR — других SAME_INVARIANT кандидатов не найдено. Learning: LOCAL_CASE_NOTE_ONLY, без promotion.

## Какие тесты прошли

poetry run pytest tests/unit/test_file_handler_buffered_input_file.py -vv --tb=short
→ 2 passed (GREEN_CONFIRMED)
- test_get_telegram_image_accepts_buffered_input_file_without_startswith
- test_get_telegram_file_accepts_buffered_input_file_without_startswith

# Какие дополнительные проверки сделали

Bounded hunt по app/ на BufferedInputFile/InputFile + startswith/endswith — CLEAR. FANIN READY, HARD_BLOCK_READY (0 open SAME_INVARIANT). Learning gate validated.

# Что не изменяли

Git commit / push / deploy не делались. Глобальные правила и class lessons не активировались (PROMOTION_DECISION=NONE).

# Оставшиеся риски

Guard узкий: isinstance(..., BufferedInputFile), не базовый InputFile. FSInputFile/URLInputFile под app/ не используются; при появлении — отдельная проверка. Worktree всё ещё uncommitted.

# Что проверить перед коммитом

Просмотреть diff app/file_handler.py и tests/unit/test_file_handler_buffered_input_file.py; при согласии — commit по Conventional Commits. Deploy отдельно.

# Технические детали

CASE_ID=BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z
FINDING_ID=FINDING-001
INVARIANT=TYPE_UNION_STR_METHOD_ON_INPUTFILE
PRODUCTION_HASH_BEFORE=sha256:7d425e30354685dfee73202234529f065ea9d45d334fc913fee114052d6fb458
PRODUCTION_HASH_AFTER=sha256:480bf4a77a3ca8ad2a467d37c1e1d7560d7b75ea5df0f5d1960e358bc4075215
TEST_CONTENT_SHA256=d6386cded0528f71e428e832d792e8eee94d3aa8eff35f5d92826e3411490169
LEARNING_VERDICT=LOCAL_CASE_NOTE_ONLY
PROMOTION_DECISION=NONE
WORKER_EXECUTION_ID=WEX/CLOSURE_OPERATOR/77a8cb9e0d
WORKTREE_STATUS=UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED=NO
