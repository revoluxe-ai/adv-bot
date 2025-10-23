# Решение проблемы с Alembic: "Can't locate revision identified by '6941eea4ae8b'"

## Что произошло?

При выполнении команды:
```bash
alembic revision --autogenerate -m "Create new init"
```

Вы получили ошибку:
```
ERROR [alembic.util.messaging] Can't locate revision identified by '6941eea4ae8b'
FAILED: Can't locate revision identified by '6941eea4ae8b'
```

## Причина ошибки

Ваша база данных содержит ссылку на старую миграцию `6941eea4ae8b`, которая больше не существует в коде. Это произошло потому, что история репозитория была "сплющена" (grafted commit), и старые миграции были удалены.

## 🚀 Быстрое решение (2 минуты)

### Вариант 1: Обновить версию в БД (Рекомендуется)

Если ваша база данных уже содержит все нужные таблицы и поля:

```bash
# Обновить метку версии в БД до текущей HEAD
poetry run alembic stamp head

# Проверить, что всё работает
poetry run alembic current
```

Вы должны увидеть: `6eb95f5a8c66 (head)`

Теперь можно создавать новые миграции:
```bash
poetry run alembic revision --autogenerate -m "Create new init"
```

### Вариант 2: Использовать скрипт-помощник

```bash
# Проверить текущее состояние
poetry run python scripts/reset_alembic.py --check

# Исправить проблему автоматически
poetry run python scripts/reset_alembic.py --stamp
```

### Вариант 3: Ручное исправление в БД

```bash
# Подключиться к базе данных
psql -U postgres -d adv_bot

# Обновить версию
UPDATE alembic_version SET version_num = '6eb95f5a8c66';

# Выйти
\q

# Проверить
poetry run alembic current
```

## 📋 Подробная инструкция

Полная документация с дополнительными вариантами и объяснениями находится в файле:
**[ALEMBIC_MIGRATION_RESET.md](./ALEMBIC_MIGRATION_RESET.md)**

## ⚠️ Если ничего не помогло

### Вариант с полным сбросом (требует бэкап!)

```bash
# 1. Создать бэкап БД
pg_dump -U postgres adv_bot > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Удалить таблицу версий Alembic
psql -U postgres -d adv_bot -c "DROP TABLE IF EXISTS alembic_version;"

# 3. Применить все миграции заново
poetry run alembic upgrade head

# 4. Проверить
poetry run alembic current
```

## 🔍 Дополнительная информация

### Текущая HEAD миграция
```
Ревизия: 6eb95f5a8c66
```

### Проверка состояния
```bash
# Показать текущую версию БД
poetry run alembic current

# Показать HEAD в коде
poetry run alembic heads

# Показать историю миграций
poetry run alembic history
```

## ❓ Почему это произошло?

1. История Git репозитория была пересоздана (см. grafted commit `4f4c1ca`)
2. Старые файлы миграций были удалены из кода
3. Но ваша база данных всё ещё хранит ссылку на старую миграцию `6941eea4ae8b`
4. При попытке создать новую миграцию, Alembic проверяет БД и не находит эту ревизию в коде

## 📚 Полезные ссылки

- [ALEMBIC_MIGRATION_RESET.md](./ALEMBIC_MIGRATION_RESET.md) - Полная документация (на английском)
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Решение других проблем
- [scripts/reset_alembic.py](./scripts/reset_alembic.py) - Скрипт-помощник

## 💡 Совет на будущее

После обновления кода из репозитория всегда проверяйте:
```bash
poetry run alembic current  # что в БД
poetry run alembic heads    # что в коде
```

Если они не совпадают, используйте `poetry run alembic stamp head`
