# ADV Bot — инвентаризация worktree (2026-09-30)

Общий клон: `/agent/repos/adv-bot`, remote `https://github.com/revoluxe-ai/adv-bot`, базовая ветка **`stage`** (`origin/stage`). Состояние git не менялось (только чтение).

## Worktrees

| Путь | Ветка | HEAD | Рабочая копия | vs `origin/stage` |
|------|--------|------|----------------|-------------------|
| `/agent/repos/adv-bot` | `stage` | `c5d3ecd88` | чисто | `stage...origin/stage` (синхрон) |

- `git worktree list --porcelain`: **один** worktree, каталога `.git/worktrees` нет.
- На этой VM других checkout’ов `adv-bot` не найдено.

## Active (что имеет смысл подхватывать)

1. **`stage` в `/agent/repos/adv-bot`** — единственная живая рабочая копия. Последние коммиты (25.09.2026): token-monitoring / shop-menu (истекающие права токена), тесты, devops LKG. Это текущая линия интеграции; сюда же стоит продолжать задачи «в stage».

2. **`origin/scripts`** (отдельного worktree **нет**, только remote) — коммиты **21.09.2026**, **не влито в `stage`**: ~862 уникальных коммитов на ветке, `stage` ушёл вперёд на ~160 коммитов (разошлись). Тема: owner-bot / strict NMID / evidence plane / scripts (DRR resolver и др.). **Открытого PR нет** — если работа по скриптам/Owner-bot ещё актуальна, её нужно поднимать через checkout ветки `scripts` (новый worktree или переключение), а не искать готовый второй каталог.

3. **Недавняя активность на remote (14 дней, не смержено в `stage`)** — по датам коммитов только `origin/scripts` плюс сами `origin/stage` / `origin/master` (релизная синхронизация).

## Skip (устаревшее / не как «текущий worktree»)

- **18 открытых PR** — последнее обновление у всех **2026-08-22**; ветки с июня–июля 2026 и старше. Примеры: #421 `customize-openspec`, #408 `ui-bidder-diagnostics`, #418/#416 тесты — выглядят как зависший бэклог, не как текущая разработка на этой машине.
- **PR #201 `worktree`** — название ветки, не git worktree; PR с марта 2026, не активен.
- Десятки **remote-веток без коммитов с 16.09.2026** (free-bot landing, auto-pause, operator/* и т.д.) — архивные ветки; подхватывать только по явному тикету.
- **`.opsx/runs/bug-cases/*`** (promobonus и др.) — следы bug-hunt с сентября 2026; не отдельные git worktree и не маркер «сейчас кодируем здесь», если координатор не назначил иначе.

## Вывод

Сейчас **физически один worktree** — общий `stage`. Вторая явная «живая» линия на GitHub — **`scripts`**, но без локального worktree и без PR; merge с `stage` потребует осознанного rebase/merge из-за сильного расхождения.
