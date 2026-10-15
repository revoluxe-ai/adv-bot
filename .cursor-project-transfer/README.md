# Cursor Project transfer — WB Sky (adv-bot portfolio)

Снимок **Project store** (Context) координатора WB Sky для переноса в новый пустой Cursor Project.

| Поле | Значение |
| --- | --- |
| Экспорт | см. `MANIFEST.json` → `exported_at` |
| Источник store | `bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089` |
| `origin/stage` при экспорте | `85fcfb85457bf589801be198cda7381206a29c06` |
| Файлов в `context/` | 231 (см. manifest) |

## Что внутри

- `context/` — зеркало store: `notes.md`, `preferences.md`, `archived.md`, `docs/`, `internal/`, `artifacts/`, `inbox/`
- `RESTORE_PROMPT.md` — **вставь в первый чат нового проекта** (одним сообщением)
- `COORDINATOR_SNAPSHOT.md` — сжатый снимок состояния портфеля на дату экспорта
- `MANIFEST.json` — список файлов и sha256

## Намеренно не в git

- `*secret*.txt` (MCP one-shot `AUTHORIZE_ONE_LIVE_RUN`) — только у Owner в безопасном хранилище
- `.docx` дубликаты active-work

После восстановления обнови `notes.md` по живому `origin/stage`, PR и CI — снимок не подменяет git.

## Обновление снимка

На машине с доступом к старому Project store:

```bash
# из корня adv-bot на stage
./.cursor-project-transfer/scripts/export-from-store.sh   # если скрипт добавлен позже
# или вручную: скопировать store → context/, пересобрать MANIFEST.json, commit stage
```
