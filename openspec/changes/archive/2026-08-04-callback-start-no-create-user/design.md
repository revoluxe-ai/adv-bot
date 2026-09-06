## Context

Callback Start сейчас зеркалит UI routing message `/start` (minimal → gate → full MainMenu), но дополнительно вызывает `create_user` внутри `sm(read_only=True)`. Owner-контракт: callback = возврат в меню для уже существующих; регистрация — на write entry-points. Unit-тесты уже characterization'ят create на callback — их нужно переписать под контракт, иначе техдолг закрепится.

## Goals / Non-Goals

**Goals:**
- Убрать создание User с callback Start path
- Сохранить pure-read session и существующий UI routing для существующего User
- Зафиксировать non-write поведение при отсутствии User
- Обновить targeted tests под контракт

**Non-Goals:**
- Менять message `/start` / gate middleware create-user
- Унифицировать `show_shops_list` gate/admin/minimal
- Менять invite/presentation UX тексты
- Менять session maker / replica topology

## Architecture Decision References

- Proposed (change-local): `openspec/changes/callback-start-no-create-user/decisions/callback-start-entry-write-path/decision.md`
- Accepted registry: релевантного accepted decision по Start entry write-path не найдено → decision proposed в change

## Ownership & Placement

- **Owner layer:** client bot UI handler Start callback (orchestration entry)
- **Allowed:** PURE_READ session, load User, Telegram UI (MainMenu / gate / minimal)
- **Forbidden:** User write/`create_user` на этом entry; write session только ради регистрации на callback
- Placement matches proposed decision: registration write остаётся у message `/start` и write middleware
- **Apply status:** decision delta implemented in `callback_start_registration` (create removed; PURE_READ retained)

## Decisions

1. **Убрать `create_user` с callback, не менять session на write**  
   Почему: Owner выбрал menu-return semantics; `read_only=True` остаётся корректным. Альтернатива «сделать alias полного `/start` через `read_only=False`» отклонена Owner'ом.

2. **При `user is None` на callback: без create; при `invite_gate` — gate UI, иначе early return**  
   Почему: близко к соседнему `show_shops_list` missing-user branch; не вводит новый onboarding write. Альтернатива «всегда silent return» хуже для invite UX; «форс `/start` текст» — лишний scope.

3. **UI routing для существующего User без изменений**  
   `use_minimal_presentation_ui` → gate (`invite_gate ∧ !passed_gate ∧ !admin`) → full MainMenu.

4. **Tests**  
   Удалить/заменить assert create_user на callback; добавить negative write-gate (create не вызывается) + missing-user non-write scenario; сохранить routing cases.

## Risks / Trade-offs

- [Risk] Пользователь без User попадает на Start-callback → не создаётся запись  
  → Mitigation: create остаётся на `/start` / middleware; gate UI при invite_gate
- [Risk] Integration tests ожидают create на callback  
  → Mitigation: targeted update assertions; narrow suite only
- [Trade-off] Callback и message `/start` больше не полные aliases по write — намеренно по Owner

## Migration Plan

1. Apply code + tests в одном change
2. Rollback: revert commit change
3. No DB migration / no feature flag

## Open Questions

- Нет блокирующих; missing-user UX зафиксирован в design decision #2

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
