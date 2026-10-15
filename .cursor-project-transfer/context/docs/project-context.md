# OPSX

Работа, которую раньше вел веб-ChatGPT. Источник правды по процессу — репозитории, не тот чат.

Стоящая инструкция, по которой продолжать разработку: [opsx-working-instruction.md](opsx-working-instruction.md).

Продуктовая стратегия adv-bot: [chatgpt-strategy-adv-bot-6abd1faa.md](chatgpt-strategy-adv-bot-6abd1faa.md). Handoff Owner (2026-10-03, обрезан): [wb-sky-handoff-cursor-project-20261003.md](wb-sky-handoff-cursor-project-20261003.md).

Этот Project — зона Owner и координатора: несколько разработок и доработка OPSX идут параллельно. Общий файл или worktree правят по очереди.

## Потоки

- Довести adv-bot (WB Sky) в концепции OPSX. Код на машине vkita-pc, checkout `C:/Users/vkita/my_code/meta-repo/adv-bot` и его worktree.
- Параллельно развивать саму технологию OPSX.
- Допилить OPSX на базе tiriel-game: контракты кривые и не сходятся, пайплайн неочевидный. Tiriel зрелее adv-bot (больше команд, upstream, верификация).

## Как устроен перенос

Переносится поверхность агента: команды, rules, pipeline, `.opsx/`. Не копируется `app/**` и не тащатся продуктовые `openspec/changes/**`. Живой перенос game → adv-bot: ветка `feature/opsx-full-command-transfer`, worktree `adv-bot-full-command-transfer`.

## Ограничения

- Субагенты на composer-2.5.
- Google Drive не использовать.
- Разработку вести только через команды. Если команда не срабатывает, правку выносить в отдельный процесс и тоже вести командами. Прямых правок нет.
- Часть обработки уже на Tempo. Подходящую `/tempo-*` для участка использовать. Одной команды на весь цикл в tiriel пока нет: шире всех `/tempo-verification` (только замороженные проверки). Цель: одна tempo-команда на весь цикл, к Owner только когда без него нельзя.
- Коммиты и пуш только по явной просьбе.
- Worker `vkita-pc` должен оставаться запущенным, иначе локальный adv-bot не виден.
- В код глубоко не лезть, пока не назван конкретный срез.

## Проверка: cloud agent vs локаль (Owner)

Cloud run координирует **git, OPSX-команды, CI, `/opsx-devops`, kubectl read-only/write по GO** (часто через self-hosted `vkita-pc`). **Не заменяет:** Telegram-кнопки wb-sky-bot, WB seller UI, браузер (будущий web-admin, tiriel-game на localhost) — это Owner на локали, либо явный Chrome CDP/MCP. Игра/фронт в облаке ≠ автоматическая «проверка сайта» на ПК Owner.
