## 1. OpenSpec / planning

- [x] 1.1 proposal, design, owner-contract, delta spec
- [x] 1.2 Architecture decision reference in design.md

## 2. Slice A — pure domain

- [x] 2.1 Feature registry + scope contract
- [x] 2.2 Resolver + product DrrProfile adapter
- [x] 2.3 DRR triple + headroom eligibility + diagnostics contract
- [x] 2.4 Unit tests

## 3. Slice B — persistence + ChangeSet dry-run

- [x] 3.1 Persistence logical slot identity — PG models, Alembic, repository, payload codec
- [x] 3.2 AdControlChangeSetV1 + `validate_ad_control_changeset` (dry-run only; no Apply Authority wiring)

## 4. Future slices

- [ ] 4.1 Runtime shop-runner integration
- [ ] 4.2 UI Advertising Control + Diagnostics
- [ ] 4.3 Headroom production allocator (Owner algorithm GO)
