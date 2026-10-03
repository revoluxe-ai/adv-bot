# Decision: Contract RETURN primary vs L0 research side

## Status

Proposed

## Context

Операторский контур `wb-api-read-only-preflight` уже умеет Owner-local L0
research archive (`wb_readonly_research.zip`) через Job `/opsx-scripts`.
Web COLLECTOR / Stage A пилот (COL-R03-009) принимает только контрактный
RETURN pack с фиксированным именем и составом. Без reusable invariant Job
exit 0 + L0 zip ошибочно воспринимаются как handoff для COLLECTOR
(инцидент smoke Job 20260805).

Accepted `openspec/decisions/scripts-wb-api-ops-stack/decision.md` закрывает
stack ownership, secret-strip и запрет объявлять Web PASS без отдельного
change, но **не** разделяет primary contract RETURN и side L0 research.
Нужен reusable domain invariant: какой артефакт является Web handoff, какой —
только Owner-local research.

## Decision

1. При активном контракте COL-R03-009 (или эквивалентном
   `artifact-class=contract_preflight`) **primary** handoff-артефактом MUST
   быть контрактный RETURN zip (+ `.sha256` sidecar) с именем и составом,
   требуемыми контрактом. L0 research zip MUST NOT быть primary и MUST NOT
   удовлетворять Web COLLECTOR accept сам по себе.
2. L0 research archive остаётся **side / opt-in** Owner-local артефактом
   (исследование, smoke). Его наличие при успешном Job MUST NOT означать
   `WEB_COLLECTOR_HANDOFF` / external handoff ready.
3. Packager и CLI gates для contract RETURN живут в том же scripts entrypoint
   классе, что и preflight/collect (`wb_api_readonly_ops`), с исполнением в
   Owner-bot Job (`/opsx-scripts`). Product apply MAY реализовать packager +
   unit; live Job / cluster delivery — ownership scripts lane, не DoD apply.
4. Honest `api_preflight=REFUSED` с exact blockers в RETURN **допустим** и
   MUST собрать primary pack. Retrofit / re-label L0 research dump в
   PASS / PASS_CANDIDATE **запрещён**.
5. Contract RETURN MUST NOT содержать token/Authorization/cookies, `shop_id`,
   raw response rows/bodies или raw request headers (строже L0: L0 может
   держать business payload после secret-strip; RETURN — attestation-only
   per contract).
6. `clean_dump` / mass collect после Web accept — отдельный artifact-class;
   без доказанного `READ_ONLY_PREFLIGHT_PASS=YES` MUST NOT выполнять API
   collect для clean_dump (exit ≠ 0, 0 API calls). Объявление самого Web
   PASS из Job по-прежнему запрещено `scripts-wb-api-ops-stack`.

## Applies to

- Capability `wb-readonly-contract-preflight-return`
- Capability `wb-api-read-only-preflight` при `--contract` /
  `--artifact-class`
- `/opsx-scripts` SCRIPTS_REPORT / known-outputs когда primary declared
- Будущие COL-R0x contract RETURN packs того же scripts/Job класса

## Allowed

- Primary: `…_COL-R03-009_RETURN.zip` + sidecar; optional side L0 рядом
- Honest REFUSED RETURN с blockers; PASS_CANDIDATE только при контрактных
  правилах contemporaneous run
- SCRIPTS_REPORT поля: `ARTIFACT_CLASS`, `PRIMARY_ARTIFACT`,
  `PRIMARY_SHA256`, side L0, `WEB_COLLECTOR_HANDOFF` /
  `EXTERNAL_HANDOFF_READY` только при primary+sha match
- Unit/fixture packager без live prod API
- Owner-bot Job invoke после green кода

## Forbidden

- Выдавать L0 `wb_readonly_research.zip` как primary при COL-R03-009 /
  `contract_preflight`
- `WEB_COLLECTOR_HANDOFF=YES` / external handoff ready без primary zip +
  matching sha
- Retrofit старого L0 dump в COL-R03-009 PASS
- shop_id / token / raw rows в RETURN
- Cursor → prod WB как execution path
- Объявление `READ_ONLY_PREFLIGHT_PASS` из Job

## Examples

Good:

- Job `--mode preflight --contract COL-R03-009 --artifact-class
  contract_preflight` → primary RETURN + sha; report
  `ARTIFACT_CLASS=contract_preflight`; L0 optional side;
  `WEB_COLLECTOR_HANDOFF=YES` только если primary на диске и sha совпал

Bad:

- Job `--mode collect` без contract → только L0 → оператор несёт L0 в
  COLLECTOR как «пакет Stage A»
- Packager копирует payload rows из L0 в evidence и ставит
  `api_preflight=PASS_CANDIDATE`
- Exit 0 без RETURN при `--contract COL-R03-009`

## Related specs

- Change delta: `specs/wb-readonly-contract-preflight-return/spec.md`
- Change delta: `specs/wb-api-read-only-preflight/spec.md`
- Stable: `openspec/specs/wb-api-read-only-preflight/spec.md`

## Related changes

- Active: `col-r03-009-contract-preflight-return`
- Prior: archived `wb-readonly-job-smoke-reports` (L0 Job smoke; не RETURN)
- Decision sibling: `openspec/decisions/scripts-wb-api-ops-stack/decision.md`

## Review checklist

- [x] existing decisions searched (`scripts-wb-api-ops-stack`,
      `orders-or-sales-reports-read-identity`,
      `wb-api-master-local-swagger-map` — не покрывают primary RETURN vs L0)
- [x] relevant decisions cited (`scripts-wb-api-ops-stack`)
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision (apply 2026-08-06: packager +
      CLI in `scripts/wb_api_readonly_ops`; Job delivery remains `/opsx-scripts`)
