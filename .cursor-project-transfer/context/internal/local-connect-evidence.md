---
cursor:
  subagentId: "bc-6d03399e-2f5b-5ffb-8303-22870dc2257c"
---

# Local project attach — evidence

Checked 2026-09-30. No git changes. No UI error was observed.

## This environment

`environment-info`:

- Personal, `recordedVia: DASHBOARD`, not deleted.
- `environmentPublicId`: `3ddff878-bcc4-11f1-977f-f6b8f2fcf9b2`
- Dashboard: https://cursor.com/dashboard/cloud-agents/environments/e/3ddff878-bcc4-11f1-977f-f6b8f2fcf9b2
- `environmentJsonPath`: null (db-backed snapshot; `environment.json` not exposed for personal environments).
- Repos already attached: `github.com/revoluxe-ai/adv-bot`, `github.com/revoluxe-ai/tiriel-game`.
- Boot build: `bld-20260930-200febdb-2089-485e-a434-e86000d88096` (`gitSetup: reuse`).

`list-self-hosted-workers` (scope all, status all): `workers: []`, `totalCount: 0`. A worker appears only while `cursor worker start` / `agent worker start` is running and registered.

`list-cloud-agents` with `isSelfHostedWorker: true` in this environment: 0 agents.

Missing from platform data: the user's PC name, and the names of the local projects that fail. Do not invent a dialog.

## Product rule

Projects run on Cloud Agents. Workspace picker lists repositories available to cloud agents (connected GitHub, GitLab, Azure DevOps, or Bitbucket Cloud). Staff forum (2026-09-23, “Create Project modal hangs…”): the picker does not list folders that exist only on the machine; a fully local Project is not available. The coordinator can still start a local agent for a step that must run on the computer.

Cloud agents clone from GitHub (Cloud and Enterprise Server), GitLab (Cloud and Self-Hosted), Azure DevOps Services, or Bitbucket Cloud, then push a branch. Read-write on the repo and dependent repos/submodules is required. Bitbucket Data Center is called out as unsupported for this path.

Cursor lists a GitHub repo only when both are true: the user can access it, and the Cursor GitHub App is installed on the account or org that owns it, with that repo included. Org repos do not appear from a personal-account install alone.

Desktop can surface a locally opened repo before the web/mobile cache does. Cache refresh is often 30–60 minutes; Desktop and cursor.com/agents have Refresh repositories.

My Machines: registered repos come from git remotes of `--worker-dir` roots. A path must exist; routing metadata is registered for each root that has a Git remote. Same Cursor account as the app. Process must stay running. `agent worker debug` checks auth, privacy routing, repo labels, and whether Cursor sees matching workers.

Picker locations “This Computer / Cloud / remote machine” open work in those places. They are a different control from the Project Workspace list.
