# /opsx-learn-from-bug

Purpose: safely append a reviewed bug, finding, correction, or engineering lesson to an existing learning/worklog file without analysing, optimizing, routing, or promoting it.

This command is an ingestion command only.

It preserves the supplied knowledge so separate optimization and verification commands can process it later.

## Modes

- default: PREVIEW ONLY / READ-ONLY
- GO: append one new learning entry to the explicitly provided target file

GO mode is active only when the user invokes:

- `/opsx-learn-from-bug GO`
- `/opsx-learn-from-bug:GO`

## Required input

The user MUST provide:

- target file:
  - exact existing learning/worklog path;
- learning input:
  - bug;
  - finding;
  - correction;
  - review result;
  - agent mistake;
  - missed invariant;
  - or complete Bug Learning Packet.

Optional metadata:

- source command;
- OpenSpec change-id;
- affected module;
- final classification;
- related diff, tests, logs, or files.

Missing optional metadata MUST NOT block capture.

If the target file is not explicitly provided or does not exist, return:

```text
Verdict:
- needs_target_file
```

MUST NOT guess or create the target path.

## Core behavior

The command MUST:

1. Read only the explicitly provided target file.
2. Preserve the supplied learning input verbatim.
3. Generate a unique learning entry ID.
4. Append exactly one entry at the end of the target file.
5. Preserve all existing content and formatting.
6. Mark the entry as pending optimization.
7. Report whether the append caused a configured size-limit overflow.

The command MUST NOT:

- diagnose why the bug was missed;
- decide where the knowledge belongs;
- classify knowledge as command, rule, template, context, or verify logic;
- inspect unrelated commands, rules, templates, specs, or source code;
- deduplicate entries;
- merge entries;
- rewrite existing entries;
- shorten or summarize the supplied input;
- fix grammar inside the supplied input;
- optimize the target file;
- promote knowledge into other artifacts;
- edit product code;
- edit OpenSpec changes or specs;
- commit, push, merge, deploy, restart services, or modify infrastructure.

Even when an identical entry appears to exist, append the new entry. Deduplication belongs to a separate optimization command.

## Entry format

Append this structure:

```text
<!-- LEARNING_ENTRY_BEGIN -->

## LEARN-<YYYYMMDD-HHMMSS>-<short-id>

- status: captured
- optimization_status: pending
- captured_at: <ISO-8601 timestamp>
- source: <provided source or not_provided>
- change_id: <provided change-id or not_provided>
- affected_area: <provided area or not_provided>
- promoted_to: none

### Raw learning input

<exact user-supplied learning input without rewriting, shortening, or omission>

<!-- LEARNING_ENTRY_END -->
```

The raw learning input MUST remain byte-for-byte equivalent where practical.

Only newline normalization required by the existing file format is allowed.

## Append rules

Before appending:

1. Confirm the target file exists.
2. Confirm the target is a regular writable text file.
3. Read the final part of the file only as needed to preserve newline separation.
4. Do not inspect or modify previous learning entries.

When appending:

- add one blank line before the entry if required;
- append the complete entry atomically where supported;
- do not replace the whole file if a safe append operation is available;
- do not sort sections;
- do not move existing content;
- do not remove duplicates;
- do not reformat headings.

If the append fails, do not leave a partial learning entry.

## Size overflow behavior

A configured size limit MUST NOT block capture.

After a successful append:

1. Check the target using the existing file-size or OpenSpec guard, if one is configured.
2. If the limit is not exceeded, return `captured`.
3. If the limit is exceeded, keep the appended entry and return `captured_with_overflow`.
4. Do not rollback the append because of size overflow.
5. Do not optimize the file during this command.
6. Recommend the separate optimizer command as the next workflow step.

If no configured limit can be found, report:

```text
overflow_check: unavailable
```

Do not invent a limit.

If the guard fails for a reason unrelated to size overflow, keep the successfully appended entry and return `captured_with_guard_failure`.

## PREVIEW mode

Default mode is read-only.

Do not edit any file.

Output:

```text
Verdict:
- preview_ready / needs_target_file

Target:
- file:

Prepared entry:
- id:
- source:
- change_id:
- affected_area:
- raw input chars:

Write status:
- not_applied

Required action:
- invoke `/opsx-learn-from-bug GO` to append this exact entry
```

Do not analyse or improve the learning input during preview.

## GO mode

Before writing:

1. Re-read the explicitly approved target file.
2. Confirm it still exists and is writable.
3. Confirm the prepared raw input has not been shortened.
4. Confirm no file other than the target will be edited.

Then append the entry.

After writing, run when available:

```bash
git diff --check -- "<target-file>"
```

If the repository contains a configured file guard that supports the target, run its file-specific check.

Do not run broad tests, product tests, or unrelated repository validation.

## GO output

```text
Verdict:
- captured / captured_with_overflow / captured_with_guard_failure / blocked

Target:
- file:

Captured entry:
- id:
- raw input chars:
- appended chars:
- status: captured
- optimization_status: pending

Overflow:
- check:
- configured limit:
- current size:
- exceeded by:

Verification:
- diff check:
- file guard:

Files changed:
- target file only:

Next step:
- none / run the separate learning optimizer
```

## Stop conditions

Stop without writing when:

- the target path was not explicitly provided;
- the target file does not exist;
- the target is not writable;
- appending would require modifying another file;
- the raw learning input is unavailable;
- the command cannot guarantee that the existing file will be preserved;
- a partial append cannot be prevented or safely recovered.

Do not stop merely because:

- the target is already oversized;
- the new entry duplicates an older entry;
- the input is poorly structured;
- classification is missing;
- the correct promotion target is unknown;
- optimization has not yet been performed.

## Required invariants

MUST preserve the original learning input.

MUST append rather than optimize.

MUST touch only the explicitly provided target file.

MUST keep the new entry after a size-limit overflow.

MUST mark every new entry as `optimization_status: pending`.

MUST NOT treat capture as approval to modify commands, rules, templates, context, specs, code, tests, CI, DB, or infrastructure.

MUST NOT claim that knowledge was promoted, deduplicated, verified, or integrated.

Capture and optimization are separate workflow stages.