# Owner Contract

## Что хотим получить

В меню магазина Telegram кнопка `📦 Выгрузить AI-пакет` запускает Full AI
Package на сервере WB Sky. Бот использует свои штатные read-only PostgreSQL и
ClickHouse. Пользователь получает ZIP в чат.

## Зачем

Локальный acceptance export зависит от локальных tunnel endpoints. Бот уже
живёт в инфраструктуре WB Sky, поэтому выгрузка из меню не должна требовать
машину пользователя.

## Что должно остаться неизменным

- Каноническая поверхность ZIP: `PackageZipAssembler.assemble_zip(shop_id, period)`.
- Идентичность export: `WBCabinet.shop_id`, не `wb_user_cabinet_id` и не
  `wb_cabinet.id`.
- Семантика пакета в `ai_package_v1`. Telegram — только transport.
- Проверка доступа — существующий seam владельца `WBUserCabinet`, без второй
  схемы авторизации.
- Read-only относительно WB и бизнес-состояния: нет WB write, campaign write,
  PG settings write, CH write, Apply Authority.

## Чего сейчас не делаем

- Второй exporter, локальные скрипты, запись в `C:\Users\...`, shell-out.
- Дата-пикер, стандартные горизонты и latest complete period в UI.
- Object storage и обрезка файлов пакета, чтобы влезть в Telegram.
- Смешение с Excel callback.
- Job-система ради V1.

## Контракт поведения

1. Callback содержит только `wb_user_cabinet_original_id`.
2. Principal — `callback.from_user.id`. Чужой кабинет: `Нет доступа к этому магазину.` Assembler не вызывается.
3. Mapping `WBUserCabinet.id` → `WBUserCabinet.wb_cabinet` → `WBCabinet.shop_id` читается read-only. Слом mapping: `Не удалось определить магазин для выгрузки.`
4. Период V1: `ExportPeriod` 2026-09-21..2026-10-04. Выбор дат спрятан в одном seam.
5. Успех: документ ZIP, имя `WB_SKY_AI_PACKAGE_<shop_id>_2026-09-21_2026-10-04.zip` (shop id санитизирован), подпись с магазином, периодом и фактом успешной сборки.
6. Перед долгой сборкой: `Формирую AI-пакет…`.
7. Сбой export/инфраструктуры или отказ отправки не из-за размера: `Не удалось сформировать AI-пакет. Попробуйте позже.` Без сырого exception и секретов.
8. Отказ Telegram по размеру: явная ошибка. ZIP не урезается и не теряет файлы.
9. Повторный клик той же пары user+cabinet, пока первая сборка идёт: `Выгрузка для этого магазина уже формируется.` Второй assembler не стартует (in-process lock).
10. Сбой транспорта не меняет семантику пакета и не пишет бизнес-состояние.

## Owner source

Текст задачи `telegram-ai-package-export` в этом change. Implementation GO
дан в том же запросе после зелёных planning gates. Merge и deploy не
разрешены.
