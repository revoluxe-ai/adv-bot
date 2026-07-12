# Decision: Mode Defaults Policy Ownership

## Status

Accepted

## Context

Mode defaults define what paid, free, and shared advertising modes enable by
default. These defaults are high-risk because several fields control WB write
actions, campaign lifecycle behavior, and paid/free product boundaries.

The motivating incident was `auto_update_minus_phrases`: the desired paid
default was first considered as a direct assignment inside
`apply_paid_auto_management_transition()`. That would have made the transition
helper own a mode-specific default, even though the project already has
declarative policy overlays for mode defaults.

## Decision

Mode-specific defaults belong to declarative mode policy overlays.

- Paid-only defaults belong in
  `app/client_bot/modules/default_settings/adv_setting_policy/paid_mode_defaults_policy.py`.
- Free-only defaults belong in
  `app/client_bot/modules/default_settings/adv_setting_policy/free_mode_defaults_policy.py`.
- Truly shared defaults belong in
  `app/client_bot/modules/default_settings/adv_setting_policy/common_mode_defaults_policy.py`.
- Transition helpers orchestrate transitions and apply overlays.
- Transition helpers do not own individual mode default values.

## Applies to

- Defaults for `AdvSetting` fields that differ between paid, free, and common
  modes.
- Paid/free mode transitions exposed through
  `apply_paid_auto_management_transition()` and `apply_free_mode_transition()`.
- UI, runner, helper, and service code paths that need mode defaults but are not
  the declarative policy owner.
- WB-impacting defaults such as automation flags, whitelist behavior, target
  place behavior, campaign lifecycle flags, and minus-phrase automation.

## Allowed

- Add a paid-only default to `PaidModeDefaultsPolicy`.
- Add a free-only default to `FreeModeDefaultsPolicy`.
- Add a truly shared default to `CommonModeDefaultsPolicy`.
- Keep transition helpers responsible for selecting and applying the correct
  overlay.
- Keep runtime runner guards that prevent WB write actions outside paid-active
  eligibility.

## Forbidden

- Direct assignment of mode defaults in transition helpers.
- Direct assignment of mode defaults in UI handlers, menu builders, runners, or
  background services.
- Treating a paid-only default as a common default.
- Treating a free-only default as a paid default.
- Relying on passing tests as proof when the default is owned by the wrong
  layer.

## Examples

Bad:

```python
def apply_paid_auto_management_transition(adv_setting, wb_cabinet):
    adv_setting.bot_active = True
    adv_setting.auto_update_minus_phrases = True
```

Good:

```python
class PaidModeDefaultsPolicy(AdvSettingDefaultsPolicy):
    rules = (
        # paid defaults
        DefaultRule(field=AdvSetting.auto_update_minus_phrases, value=True),
    )


class FreeModeDefaultsPolicy(AdvSettingDefaultsPolicy):
    rules = (
        # free defaults
        DefaultRule(field=AdvSetting.auto_update_minus_phrases, value=False),
    )
```

## Related specs

- `openspec/changes/enable-minus-phrases-on-bot-active/specs/paid-minus-phrases-default/spec.md`

## Related changes

- `openspec/changes/enable-minus-phrases-on-bot-active/`

## Review checklist

- [ ] Existing decisions were searched before choosing a placement.
- [ ] `openspec/decisions/mode-defaults-policy-ownership/decision.md` is cited
      from the change design when mode defaults are touched.
- [ ] Paid-only defaults are owned by `PaidModeDefaultsPolicy`.
- [ ] Free-only defaults are owned by `FreeModeDefaultsPolicy`.
- [ ] Truly shared defaults are owned by `CommonModeDefaultsPolicy`.
- [ ] Transition helpers only orchestrate transitions and apply overlays.
- [ ] UI, runner, helper, and service layers do not assign mode default values.
