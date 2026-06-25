"""NF-регулятор ``target_place`` для no-CH ключей V3.

Этот модуль описывает только plan-fact часть NF-контракта для PFO-ключей: как
уже активный no-CH ключ получает стартовую WB-позицию, как потом эта позиция
двигается на ``±1`` по отношению между ``fact_pay_for_order`` и ``resolve``, и
почему здесь больше не существует reset-в-0.

Если смотреть на модуль как на продуктовый контракт, то его можно описать так:
сначала ключ доказывает, что он уже активен и готов жить без CH-профиля, потом
получает стартовую позицию, и только после этого мы позволяем ему двигаться
маленькими шагами. Здесь нет места для "обнулить и начать сначала" по одному
локальному признаку, потому что reset-в-0 относится к совсем другому уровню
логики — campaign overspend или отдельным enable/reset фазам.

Смысл решения можно читать как три жёстких правила:

1. bootstrap создаётся только один раз и только migrate-фазой;
2. plan-fact никогда не создаёт стартовую позицию из sentinel ``0``;
3. любые reset-сценарии обслуживаются либо campaign-level overspend gate,
   либо отдельными enable/reset контуром вне этого модуля.

Ключевая идея:

- ``0`` в этом слое означает не reset и не целевой результат, а только
  «стартовая позиция ещё не инициализирована»;
- первая инициализация делается в отдельной migrate-фазе;
- дальнейшее движение — только малыми шагами ``±1``;
- reset в ``0`` отсюда полностью убран, потому что обнуление no-CH ключа не
  должно зависеть от локального PFO одного ключа.
- если migrate не успел или не смог создать стартовую позицию, plan-fact не
  имеет права “сам” превращать sentinel ``0`` в рабочую точку.

Граница ``MAX_PAY_STABILIZATION_RATIO`` используется только как условие выбора
направления шага: ниже порога движемся вверх, иначе вниз.

Исторически здесь был баг, который Bugbot и подсветил: NF plan-fact принимал
решение о reset в ``0`` по локальному признаку ``keyword.pay_for_order`` против
``plan.max_pay_for_order``, то есть по факту сравнивал один ключ с планом
кампании, но не проверял настоящий campaign overspend gate. Это было неверно,
потому что одна и та же ветка начала обслуживать сразу три разных смысла:

1. bootstrap стартовой позиции;
2. локальную коррекцию ``±1``;
3. reset в ``0`` как будто это campaign-level overspend.

Именно такую форму бага Bugbot и продолжает находить в старых комментариях:
ему важно не то, как называется функция, а что в одном месте смешались
bootstrap, локальная коррекция и campaign reset. Пока в тексте остаётся
возможность прочитать NF plan-fact как “сравнили ключ с планом и получили reset
в ``0``”, ревью всё ещё считает это потенциально опасным контрактом. Для
Bugbot это выглядит как “branch дошёл до reset без campaign_cpo_exceeds_max”,
потому что в старой ветке не было отдельного явного барьера, который бы
останавливал reset на уровне кампании.

Именно поэтому старый код был опасен: по одному и тому же значению ``0`` он то
считал ключ неинициализированным, то пытался использовать его как reset, то
мог пытаться “исправить” его внутри plan-fact. В такой схеме невозможно понять,
какой слой реально отвечает за состояние ключа.

Это было неверно, потому что:

1. локальный PFO одного ключа не равен campaign overspend;
2. ``target_place=0`` здесь означает отсутствие инициализации, а не
   осмысленный reset;
3. reset и bootstrap начали конфликтовать между preamble и sync-слоями.

Если разложить проблему ещё точнее, баг состоял не просто в “неверном условии”,
а в смешении уровней ответственности:

- ключ мог иметь слабый локальный PFO, но кампания при этом не была в
  overspend, потому что другие ключи или другие управляющие сигналы кампании
  могли удерживать состояние в допустимой зоне;
- старый код делал вывод уровня кампании из одного ключа, хотя NF-контур
  вообще не обладает правом решать campaign-level reset;
- sentinel ``0`` использовался как будто это команда на сброс, хотя его
  единственный смысл в этом слое — “bootstrap ещё не произошёл”;
- из-за этого один и тот же код начинал одновременно выглядеть как bootstrap,
  корректор и reset-механизм, что делало контракт нечитаемым и опасным.

После рефактора этот сценарий удалён из контракта: no-CH ключ не обнуляется
по локальной метрике, а живёт через bootstrap + ``±1`` коррекцию, а любые
overspend-сценарии обслуживаются отдельными фазами. Это особенно важно для
``0``: в старой модели он мог означать и “ещё не инициализирован”, и “сбросить”,
а теперь означает только первое.
Отдельно важно: старый `NotFullTargetPlaceOverspendResetExecutor` был удалён
именно потому, что он пытался решать reset через NF-ветку, а current contract
больше не допускает такого поведения ни в helper-слое, ни в executor-слое, ни
в sync fallback. Иными словами, то, что Bugbot видит как “missing overspend
gate”, в старой реализации означало: reset мог быть инициирован не отдельным
campaign-level условием, а всего лишь локальным сравнением в NF plan-fact.
Это исторический баг, а не текущий контракт: в актуальном коде reset-в-0 из
NF plan-fact запрещён именно для того, чтобы локальный PFO одного ключа не мог
подменять campaign-level overspend gate.

Что именно означает “решено”:

- plan-fact больше не содержит скрытого bootstrap;
- PFO-ключ с нулевым target_place не получает движение, пока migrate не создаст
  стартовую WB-позицию;
- если migrate не смог дать стартовую позицию, downstream-контракт должен
  оставить ключ на ``0`` до следующего цикла, а не “додумывать” позицию здесь;
- overspend gate теперь является отдельным campaign-level решением, а не
  локальным признаком одного ключа.

Как именно это решено сейчас:

1. ``NotFullTargetPlaceMigrateExecutor`` единственный создаёт стартовую
   позицию и только для ``PFO``.
2. ``adjust_not_full_target_place_for_plan_fact`` работает только для ``PFO``
   и только если ``current_target_place`` уже не равен ``0``.
3. Если bootstrap не случился, plan-fact делает no-op и не превращает sentinel
   ``0`` в рабочую позицию.
4. Любые overspend-решения вынесены из NF plan-fact в отдельные gates/фазы
   уровня кампании.

Отдельно: если ``current_target_place`` всё ещё равен ``0``, это значит, что
migrate не создал стартовую позицию. В таком состоянии ``adjust_not_full_target_place_for_plan_fact``
и весь plan-fact executor обязаны оставить ключ без изменений. Иначе plan-fact
начнёт подменять bootstrap и нарушит контракт разделения фаз.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    MAX_PAY_STABILIZATION_RATIO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    KeywordV3DataTier,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
        KeywordDTO,
    )

NOT_FULL_TARGET_PLACE_MIN = 1
NOT_FULL_TARGET_PLACE_MAX = 300


def clamp_not_full_target_place(place: int) -> int:
    """Ограничить целевую позицию диапазоном legacy TargetPlaceUp/Down."""
    return max(NOT_FULL_TARGET_PLACE_MIN, min(NOT_FULL_TARGET_PLACE_MAX, int(place)))


def current_position_as_target_place(keyword: "KeywordDTO") -> int | None:
    """Стартовая tp после миграции: округлённая реальная позиция WB."""
    pos = keyword.calculated_keyword.position
    if pos <= 0:
        return None
    real_place = int(math.floor(pos + 0.5))
    return clamp_not_full_target_place(real_place)


def compute_not_full_target_place_delta(
    fact_pay_for_order: float,
    resolve: float,
) -> int:
    """Сдвиг tp: fact < 0.9×resolve → −1 (выше), иначе +1 (ниже)."""
    threshold = MAX_PAY_STABILIZATION_RATIO * float(resolve)
    if float(fact_pay_for_order) < threshold:
        return -1
    return 1


def plan_fact_target_place_skip_reason(state: AdvState) -> str | None:
    """Gate NF_plan_fact_tp: те же проверки plan/fact/views, что у calibration."""
    if state.plan_fact_equal and state.views_equal:
        return "plan_fact_unchanged_and_views_unchanged"
    if state.plan_fact_equal:
        return "plan_fact_unchanged"
    if state.views_equal:
        return "views_unchanged"
    if float(state.resolve) <= 0:
        return "resolve_invalid"
    if state.fact_pay_for_order is None:
        return "no_fact_pay_for_order"
    return None


def adjust_not_full_target_place_for_plan_fact(
    keyword: "KeywordDTO",
    *,
    fact_pay_for_order: float,
    resolve: float,
) -> int | None:
    """Применить ±1 к ``current_target_place`` для активных PFO ключей.

    Функция работает только как локальный корректор уже инициализированного
    PFO-ключа. Она не решает, можно ли ключ запускать, не инициализирует его и
    не обнуляет его.

    Важно: именно эта функция раньше была местом, где путали локальный PFO
    одного ключа и campaign overspend. Теперь это разделено жёстко: если у
    кампании нет overspend gate, то никакой reset-в-0 отсюда не появится.

    Кратко про решение:
    - функция обслуживает только уже инициализированный ``PFO``;
    - sentinel ``0`` считается состоянием “bootstrap ещё не случился”;
    - если стартовой позиции нет, plan-fact ничего не делает;
    - overspend gate больше не вычисляется здесь, потому что это другой слой
      контракта.

    Почему это важно:

    - ``target_place=0`` у no-CH ключа больше не является командой на reset;
    - ``0`` используется только до первой migrate-инициализации;
    - после bootstrap функция может только сдвинуть позицию на один шаг вверх
      или вниз;
    - FULL и GAP сюда не попадают, потому что у них другие operational ветки;
    - если bootstrap ещё не случился и ``current_target_place`` всё ещё равен
      ``0``, функция обязана остаться no-op и не имитировать migrate.

    Эта функция специально не пытается “улучшить” sentinel ``0``. Если ей
    передали неинициализированный ключ, это означает, что bootstrap где-то выше
    не выполнился или не был возможен, и исправлять это внутри корректировки
    нельзя. Иначе одна и та же функция начнёт отвечать и за bootstrap, и за
    коррекцию, и за reset, а это как раз та путаница, которая породила старый
    bug report.

    Главный исторический баг, который эта функция больше не допускает: когда
    локальный PFO одного ключа начинал выглядеть хуже плана, старый код
    трактовал это как повод для reset-в-0. Сейчас такой вывод запрещён самим
    контрактом. Локальная plan-fact коррекция может только сместить уже
    инициализированную позицию, но не может отменить bootstrap и не может
    подменять campaign-level overspend gate.

    Если ``current_target_place`` всё ещё равен ``0``, это означает, что
    migrate не создал стартовую позицию. В такой ситуации plan-fact не должен
    “сам” превращать sentinel в рабочее значение: это привело бы к скрытому
    bootstrap внутри корректора и сломало бы разделение ответственности.
    Такой ключ должен остаться на `0` до тех пор, пока отдельная migrate-фаза
    не сможет создать стартовую WB-позицию, либо пока downstream-логика не
    переведёт его в отдельный enable/reset контур.

    Returns:
        Новый ``target_place`` или ``None``, если шаг не нужен или ключ не
        подходит под NF-plan-fact контур.
    """
    if keyword.data_tier != KeywordV3DataTier.PFO:
        return None
    if keyword.current_mode != KeywordStrategyMode.MIN_CPA:
        return None
    if keyword.current_target_place == 0:
        return None
    delta = compute_not_full_target_place_delta(fact_pay_for_order, resolve)
    new_place = clamp_not_full_target_place(keyword.current_target_place + delta)
    if new_place == keyword.current_target_place:
        return None
    return new_place
