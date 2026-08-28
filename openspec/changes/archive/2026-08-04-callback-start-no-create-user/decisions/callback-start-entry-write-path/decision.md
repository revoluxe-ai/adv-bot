# Decision: Callback Start entry write-path

## Status

Proposed (implemented in change; promote to accepted on archive)

## Context

В client bot есть два Start entry: message `/start` (регистрация + меню) и callback Start (кнопка «вернуться в меню»). Смешение write (`create_user`) с pure-read session на callback даёт неверный write-path и закрепляет техдолг тестами. Нужен reusable invariant: кто владеет созданием User и какой session mode допустим на каждом entry.

## Decision

Создание `User` принадлежит только write entry-points (message `/start` registration и middleware/handlers с явным `sm(read_only=False)`). Callback Start — menu-return entry: только PURE_READ session и UI routing (minimal / gate / full menu). На callback Start path MUST NOT вызывать `create_user` и MUST NOT открывать write session ради регистрации.

## Applies to

- Client bot Start callback entry (возврат в стартовое меню)
- Client bot message `/start` registration entry
- Любые будущие «alias меню» callbacks, которые зеркалят стартовый экран без onboarding write

## Allowed

- Callback Start: `sm(read_only=True)`, load User, показать MainMenu / gate / minimal UI
- Message `/start` / gate middleware: `sm(read_only=False)` + `create_user` при отсутствии User
- При отсутствии User на callback Start: non-write outcome (early return и/или gate UI без create)

## Forbidden

- `create_user` (или иной User INSERT/commit) внутри callback Start path
- `sm(read_only=True)` paired with User create/commit на том же session scope
- Скрытая регистрация через menu-return callback как обход `/start`

## Examples

**Good:** callback Start загружает существующего User read-only и вызывает `MainMenu` / gate.  
**Good:** message `/start` создаёт User через write session.  
**Bad:** callback Start при `user is None` вызывает `create_user` под `read_only=True`.  
**Bad:** перенос create на callback «на всякий случай», сохраняя read-only session.

## Related specs

- `openspec/changes/callback-start-no-create-user/specs/callback-start-menu-return/spec.md`

## Related changes

- `openspec/changes/callback-start-no-create-user`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited (accepted write-path decision for this entry отсутствовал)
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
