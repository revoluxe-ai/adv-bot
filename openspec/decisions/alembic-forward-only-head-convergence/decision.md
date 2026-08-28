# Decision: Forward-only слияние Alembic head

## Status

Accepted

## Context

Граф Alembic может временно получить несколько конечных ревизий из-за
параллельных ветвей разработки. Для его схождения нужен повторно применимый
инвариант: опубликованная история миграций неизменяема, а топология приводится
к одной head только новой forward-only merge-ревизией.

## Decision

Схождение нескольких Alembic head принадлежит слою миграционной топологии.
Он выполняется новой merge-ревизией, которая ссылается на все текущие head и
не содержит schema- или data-операций, если целью является только слияние
ветвей. Существующие опубликованные ревизии не переписываются, не удаляются и
не получают изменённые parent-ссылки.

Ожидаемая единственная итоговая head должна проверяться контрактным тестом,
чтобы дальнейшие миграции продолжали однозначный граф.

## Applies to

- Alembic-ревизии и их `down_revision`;
- изменения, устраняющие несколько конечных head;
- контрактные проверки итоговой Alembic head.

## Allowed

- Добавлять одну новую forward-only merge-ревизию с несколькими родителями.
- Оставлять `upgrade()` и `downgrade()` без операций при чисто топологическом
  слиянии.
- Обновлять ожидаемую итоговую head в выделенной контрактной проверке.
- Продолжать будущие миграции от новой единственной head.

## Forbidden

- Изменять, удалять или переписывать существующие опубликованные ревизии для
  устранения нескольких head.
- Добавлять DDL, миграцию данных или прикладную логику в merge-ревизию, цель
  которой ограничена схождением топологии.
- Сохранять несколько ожидаемых конечных head после merge-изменения.
- Подменять контрактную проверку непроверяемым ручным утверждением о графе.

## Examples

- Хорошо: две параллельные конечные ревизии получают одну новую merge-ревизию
  с обеими в `down_revision`; операции схемы и данных отсутствуют.
- Плохо: одна из существующих ревизий изменяется так, чтобы указывать на
  другую конечную ревизию, либо merge-ревизия заодно создаёт таблицу.

## Related specs

- `openspec/specs/alembic-head-convergence/spec.md`

## Related changes

- `openspec/changes/archive/2026-08-17-merge-alembic-heads` (archived from `merge-alembic-heads`)

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
- [x] implementation conformance and write scope reconciled
- [x] independent review completed on archive
