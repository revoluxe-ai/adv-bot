# 03_HANDOFF_SCHEMAS — preview report (R40)

## Schema id

`opsx-resolve-conflict/preview-report/v2`

## Required top-level fields

| Field | Meaning |
|---|---|
| `CURRENT_CONFLICT` | operation, selected `path`, stage OIDs, availability flags; `unmerged_paths_inventory` / `all_unmerged_paths` are inventory only (`all_unmerged_paths_role=inventory_not_analyzed`) |
| `FACTS` | observed Git/code facts only (selected path) |
| `OURS` / `THEIRS` | concise side explanations |
| `SEMANTIC_CONFLICT` | behavioral/contract disagreement vs textual overlap |
| `CONTEXT` | `paths_analyzed` = exactly `[selected path]`; inventory note |
| `INTERPRETATIONS` | inferred meanings; each marked inference |
| `OWNER_DECISIONS_REQUIRED` | unprovable product/architecture choices |
| `RESOLUTION_OPTIONS` | ≥2 coherent options when evidence supports |
| `RECOMMENDATION` | one option or `null` if unjustified |
| `VALIDATION_PLAN` | targeted checks |
| `LIMITATIONS` | advisory / missing producer / missing sandbox / open findings |
| `MUTATION_ASSERTION` | worktree/index/refs unchanged + digests |
| `command_ledger` | allowlisted Git argv evidence |
| `human_report_ru` | Russian rendering with safety label |

## CLI STOP envelope

Non-success preview conditions use existing
`opsx-resolve-conflict/cli-stop-envelope/v1` via `StopRequired`.

Multi-conflict without `--path`:

```text
reason=PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS
details.unmerged_paths=[sorted repository-relative paths]
```
