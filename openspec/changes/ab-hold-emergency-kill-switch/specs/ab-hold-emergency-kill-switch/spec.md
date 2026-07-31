## ADDED Requirements

### Requirement: Emergency control visible only under A/B Hold
Система MUST показывать управление Emergency только когда режим A/B Hold кампании не равен `OFF` (включая PENDING_SETUP, WARM_UP, ACTIVE и прочие non-OFF фазы). При Hold `OFF` кнопка Emergency MUST NOT быть доступна на ordinary экранах кампании.

#### Scenario: Hold OFF hides Emergency
- **WHEN** пользователь открывает меню кампании и A/B Hold mode = `OFF`
- **THEN** система MUST NOT показывать кнопку Emergency

#### Scenario: Hold non-OFF shows Emergency
- **WHEN** пользователь находится в UI A/B Hold и mode ≠ `OFF`
- **THEN** система MUST показывать кнопку Emergency

### Requirement: Launch education before relying on Emergency
На странице запуска A/B Hold система MUST объяснить пользователю, что делает Emergency (пауза РК, блок ключей, запрет пополнения бюджета, сигнал что что-то сильно не так). Образование MUST требовать явного Confirm/ACK. Silent button без объяснения Forbidden.

#### Scenario: Launch requires ACK of Emergency meaning
- **WHEN** пользователь проходит страницу запуска A/B Hold
- **THEN** система MUST показать объяснение Emergency и MUST принять Confirm/ACK до того, как полагаться на silent наличие кнопки

### Requirement: Confirm before Emergency executes
Перед исполнением Emergency система MUST запросить короткое явное подтверждение («Точно остановить?» или эквивалент). Без подтверждения мутации MUST NOT выполняться.

#### Scenario: Cancel confirm does nothing
- **WHEN** пользователь нажимает Emergency и отменяет confirm
- **THEN** система MUST NOT ставить РК на паузу, MUST NOT блокировать ключи и MUST NOT включать Emergency latch

#### Scenario: Confirm executes kill switch
- **WHEN** пользователь подтверждает Emergency
- **THEN** система MUST выполнить паузу РК, блок всех ключей и включение durable Emergency latch

### Requirement: Emergency stops spend immediately
После подтверждённого Emergency система MUST:
1. поставить кампанию (Search+Auto пары ComplexAdv в scope) на паузу;
2. заблокировать все ключи кампании;
3. включить durable Emergency latch, при котором бюджет MUST NOT пополняться и activity-control MUST NOT возобновлять кампанию / top-up, пока latch активен.

Hold mode MUST NOT автоматически переводиться в `OFF` только из-за Emergency.

#### Scenario: Confirmed Emergency pauses blocks and latches
- **WHEN** Emergency подтверждён и latch ещё не активен
- **THEN** система MUST поставить РК на паузу, MUST заблокировать все ключи и MUST установить активный Emergency latch без EXIT Hold в `OFF`

#### Scenario: Activity control respects latch
- **WHEN** Emergency latch активен
- **THEN** система MUST NOT выполнять budget top-up и MUST NOT рестартовать кампанию через ordinary activity-control / auto-budget пути

### Requirement: Emergency is idempotent
Если Emergency latch уже активен, повторное подтверждение Emergency MUST быть идемпотентным no-op с честным статусом (без ложного «успех как первый раз» и без частичных повторных мутаций как будто с нуля).

#### Scenario: Double press with active latch
- **WHEN** Emergency latch уже активен и пользователь снова подтверждает Emergency
- **THEN** система MUST сообщить, что авария уже активна, и MUST NOT требовать повторного полного «успешного» цикла как первого запуска

### Requirement: Immediate support contact on Emergency
После подтверждённого Emergency (и при показе состояния активной аварии) система MUST сразу предложить контакт с поддержкой через существующую ссылку администратора (`SUPPORT_LINK`). Тихий возврат без контакта Forbidden.

#### Scenario: Result screen includes support link
- **WHEN** Emergency выполнен или пользователь видит активный аварийный статус
- **THEN** система MUST показать ссылку/кнопку поддержки на чат администратора

### Requirement: Clear Emergency and return to normal is out of MVP
MVP MUST NOT предоставлять one-tap «снять аварийный стоп и сбросить в обычный режим». Такое действие MAY быть добавлено later; до этого снятие аварии — через поддержку.

#### Scenario: MVP has no self-serve clear
- **WHEN** Emergency latch активен в MVP
- **THEN** система MUST NOT предлагать пользователю самообслуживаемое снятие latch и полный сброс в ordinary mode без участия поддержки
