/**
 * OPSX central catalog helper — committed allowlist snapshot sync + incremental index.
 *
 * Usage:
 *   node .opsx/tools/opsx-central-catalog.mjs snapshot-plan [--repo <path>]
 *   node .opsx/tools/opsx-central-catalog.mjs snapshot-apply [--repo <path>] [--head-only]
 *   node .opsx/tools/opsx-central-catalog.mjs index-plan
 *   node .opsx/tools/opsx-central-catalog.mjs index-apply
 *
 * Index also fingerprints the sorted command path set as STRUCTURE_HASH
 * (sha256 integrity; not path encryption) and emits STRUCTURE_CHANGED on drift.
 *
 * No third-party deps. Uses Node built-ins + git CLI.
 */
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
  copyFileSync,
} from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, "../..");

function die(msg, code = 1) {
  console.error(msg);
  process.exit(code);
}

function sh(args, opts = {}) {
  const r = spawnSync(args[0], args.slice(1), {
    encoding: "utf8",
    cwd: opts.cwd || PROJECT_ROOT,
    maxBuffer: 64 * 1024 * 1024,
  });
  if (r.error) throw r.error;
  if ((r.status ?? 1) !== 0 && !opts.allowFail) {
    throw new Error(
      `${args.join(" ")} failed: ${(r.stderr || r.stdout || "").trim()}`,
    );
  }
  return (r.stdout || "").trim();
}

function sha256(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

/** Path-set integrity fingerprint (sorted COMMAND_PATH lines only). */
function structureHashFromPaths(paths) {
  const h = createHash("sha256");
  for (const p of [...paths].sort()) {
    h.update(p);
    h.update("\n");
  }
  return h.digest("hex");
}

function pathsForSource(occMap, sourceId) {
  const out = [];
  const prefix = sourceId + "::";
  for (const [key, row] of occMap) {
    if (key.startsWith(prefix)) out.push(row.COMMAND_PATH);
  }
  return out.sort();
}

function pathSetDiff(prevPaths, nextPaths) {
  const prev = new Set(prevPaths);
  const next = new Set(nextPaths);
  return {
    added_paths: nextPaths.filter((p) => !prev.has(p)),
    removed_paths: prevPaths.filter((p) => !next.has(p)),
  };
}

function parseSimpleYaml(text) {
  // Minimal JSON-compatible YAML subset: key: value, nested 2-space maps, lists with - item
  // For config we accept either YAML-like or JSON.
  const trimmed = text.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    return JSON.parse(trimmed);
  }
  const lines = text.split(/\r?\n/);
  const root = {};
  const stack = [{ indent: -1, obj: root, key: null, isList: false }];
  for (const raw of lines) {
    if (!raw.trim() || raw.trim().startsWith("#")) continue;
    const indent = raw.match(/^ */)[0].length;
    const line = raw.trim();
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) {
      stack.pop();
    }
    const parent = stack[stack.length - 1];
    if (line.startsWith("- ")) {
      const val = coerce(line.slice(2).trim());
      if (!Array.isArray(parent.obj[parent.key])) parent.obj[parent.key] = [];
      if (typeof val === "object" && val !== null) {
        parent.obj[parent.key].push(val);
        stack.push({ indent, obj: val, key: null, isList: false });
      } else {
        parent.obj[parent.key].push(val);
      }
      continue;
    }
    const m = line.match(/^([^:]+):\s*(.*)$/);
    if (!m) continue;
    const key = m[1].trim();
    const rest = m[2];
    if (rest === "") {
      parent.obj[key] = {};
      stack.push({ indent, obj: parent.obj[key], key, isList: false });
    } else {
      parent.obj[key] = coerce(rest);
      parent.key = key;
    }
  }
  return root;
}

function coerce(v) {
  if (v === "true") return true;
  if (v === "false") return false;
  if (/^-?\d+$/.test(v)) return Number(v);
  if (
    (v.startsWith('"') && v.endsWith('"')) ||
    (v.startsWith("'") && v.endsWith("'"))
  ) {
    return v.slice(1, -1);
  }
  return v;
}

function loadSources(repoRoot = PROJECT_ROOT) {
  const p = join(repoRoot, ".opsx/sources.yaml");
  if (!existsSync(p)) die(`missing ${p}`);
  const text = readFileSync(p, "utf8");
  if (text.trim().startsWith("{")) return JSON.parse(text);
  // Line-oriented subset for this schema only.
  const cfg = {
    schema_version: 1,
    repo_family_id: "unknown",
    central_root: "../opsx-central",
    catalog_relpath: "catalog",
    sources_relpath: "sources",
    allowlist: [],
    hard_exclude: [],
  };
  let listKey = null;
  for (const raw of text.split(/\r?\n/)) {
    if (!raw.trim() || raw.trim().startsWith("#")) continue;
    const list = raw.match(/^\s*-\s+(.*)$/);
    if (list && listKey) {
      let v = list[1].trim();
      if (
        (v.startsWith('"') && v.endsWith('"')) ||
        (v.startsWith("'") && v.endsWith("'"))
      ) {
        v = v.slice(1, -1);
      }
      cfg[listKey].push(v);
      continue;
    }
    const kv = raw.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!kv) continue;
    const key = kv[1];
    const rest = kv[2].trim();
    if (key === "allowlist" || key === "hard_exclude") {
      listKey = key;
      cfg[key] = [];
      continue;
    }
    listKey = null;
    if (rest !== "") cfg[key] = coerce(rest);
  }
  return cfg;
}

function normalizeBranch(name) {
  return String(name || "unknown")
    .replace(/[^A-Za-z0-9._/-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/\//g, "__");
}

function matchGlob(rel, pattern) {
  // Very small glob: ** and * only, / separators
  const esc = pattern
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*\*/g, "<<DS>>")
    .replace(/\*/g, "[^/]*")
    .replace(/<<DS>>/g, ".*");
  return new RegExp(`^${esc}$`).test(rel.replace(/\\/g, "/"));
}

function isHardExcluded(rel, hard) {
  const n = rel.replace(/\\/g, "/");
  const rules = Array.isArray(hard) ? hard : [];
  if (n === ".git" || n.startsWith(".git/")) return true;
  if (n.includes("/.git/") || n.endsWith("/.git")) return true;
  for (const p of rules) {
    if (matchGlob(n, p) || matchGlob(n, p.replace(/^\*\*\//, ""))) return true;
    if (p.endsWith("/**") && n.startsWith(p.slice(0, -3))) return true;
  }
  if (/(^|\/)\.env($|\.)/.test(n)) return true;
  if (n.includes("node_modules/")) return true;
  return false;
}

function isAllowlisted(rel, allow, hard) {
  const n = rel.replace(/\\/g, "/");
  if (isHardExcluded(n, hard)) return false;
  const rules = Array.isArray(allow) ? allow : [];
  for (const p of rules) {
    if (matchGlob(n, p)) return true;
    if (p.endsWith("/**") && (n === p.slice(0, -3) || n.startsWith(p.slice(0, -3) + "/"))) {
      return true;
    }
    if (!p.includes("*") && (n === p || n.startsWith(p + "/"))) return true;
  }
  return false;
}

function listCommittedAllowlist(repoRoot, cfg) {
  const out = sh(["git", "-C", repoRoot, "ls-tree", "-r", "--name-only", "HEAD"]);
  const files = out ? out.split(/\r?\n/).filter(Boolean) : [];
  return files.filter((f) => isAllowlisted(f, cfg.allowlist, cfg.hard_exclude));
}

function gitShow(repoRoot, revPath) {
  return spawnSync("git", ["-C", repoRoot, "show", revPath], {
    encoding: "buffer",
    maxBuffer: 64 * 1024 * 1024,
  });
}

function dirtyAllowlisted(repoRoot, paths) {
  const set = new Set(paths.map((p) => p.replace(/\\/g, "/")));
  const names = new Set();
  for (const args of [
    ["git", "-C", repoRoot, "diff", "--name-only"],
    ["git", "-C", repoRoot, "diff", "--name-only", "--cached"],
    ["git", "-C", repoRoot, "ls-files", "--others", "--exclude-standard"],
  ]) {
    const out = sh(args, { allowFail: true });
    for (const line of out.split(/\r?\n/).filter(Boolean)) {
      const name = line.replace(/\\/g, "/");
      if (set.has(name)) names.add(name);
    }
  }
  return [...names];
}

function ensureSnapshotRepo(snapshotDir) {
  mkdirSync(snapshotDir, { recursive: true });
  if (!existsSync(join(snapshotDir, ".git"))) {
    sh(["git", "init"], { cwd: snapshotDir });
    sh(["git", "config", "user.email", "opsx-central@local"], { cwd: snapshotDir });
    sh(["git", "config", "user.name", "OPSX Central"], { cwd: snapshotDir });
  }
}

function writeSourceYaml(snapshotDir, meta) {
  const lines = [
    `schema_version: 1`,
    `repo_family_id: ${meta.repo_family_id}`,
    `branch_id: ${meta.branch_id}`,
    `source_repo: ${JSON.stringify(meta.source_repo)}`,
    `source_branch: ${JSON.stringify(meta.source_branch)}`,
    `source_commit: ${meta.source_commit}`,
    `safe_tree_hash: ${meta.safe_tree_hash}`,
    `published_at_utc: ${meta.published_at_utc}`,
  ];
  writeFileSync(join(snapshotDir, "SOURCE.yaml"), lines.join("\n") + "\n", "utf8");
}

function safeTreeHash(repoRoot, files) {
  const h = createHash("sha256");
  for (const f of [...files].sort()) {
    const r = gitShow(repoRoot, `HEAD:${f}`);
    if (r.status !== 0) continue;
    h.update(f);
    h.update("\0");
    h.update(r.stdout);
    h.update("\0");
  }
  return h.digest("hex");
}

function snapshotPaths(cfg, branch, repoRoot = PROJECT_ROOT) {
  const root = resolve(repoRoot, cfg.central_root);
  const family = cfg.repo_family_id || "unknown";
  const branchId = normalizeBranch(branch);
  return {
    centralRoot: root,
    snapshotDir: join(root, cfg.sources_relpath || "sources", family, branchId),
    catalogDir: join(root, cfg.catalog_relpath || "catalog"),
    sourceId: `${family}/${branchId}`,
    branchId,
  };
}

function extractCanonical(buf) {
  const text = buf.toString("utf8");
  const begin = "# BEGIN CANONICAL SOURCE BODY\n";
  const end = "# END CANONICAL SOURCE BODY\n";
  const i = text.indexOf(begin);
  const j = text.indexOf(end);
  if (i >= 0 && j > i) {
    return text.slice(i + begin.length, j);
  }
  return text;
}

function parseFrontmatter(text) {
  if (!text.startsWith("---")) return {};
  const end = text.indexOf("\n---", 3);
  if (end < 0) return {};
  const block = text.slice(3, end).trim();
  const out = {};
  for (const line of block.split(/\r?\n/)) {
    const m = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    out[m[1]] = v;
  }
  return out;
}

function commandMetaFromFile(rel, buf) {
  const full = buf.toString("utf8");
  const outer = parseFrontmatter(full);
  const canonical = extractCanonical(buf);
  const embedded = parseFrontmatter(canonical);
  const stem = rel.split("/").pop().replace(/\.md$/, "");
  return {
    component_id: outer.component_id || embedded.id || stem,
    component_version: outer.component_version || "",
    purpose: embedded.description || "",
    aliases: outer.aliases_of ? [outer.aliases_of] : [],
    tags: [],
    full_file_hash: sha256(buf),
    canonical_body_hash: sha256(Buffer.from(canonical, "utf8")),
    contract_hash: sha256(
      Buffer.from(
        [
          outer.contract_id || "",
          embedded.name || "",
          embedded.id || "",
          embedded.description || "",
        ].join("\n"),
        "utf8",
      ),
    ),
  };
}

function cmdSnapshotPlan(repoRoot, headOnly, { quiet = false } = {}) {
  const cfg = loadSources(repoRoot);
  const branch = sh(["git", "-C", repoRoot, "branch", "--show-current"]) || "DETACHED";
  const head = sh(["git", "-C", repoRoot, "rev-parse", "HEAD"]);
  const files = listCommittedAllowlist(repoRoot, cfg);
  const dirty = dirtyAllowlisted(repoRoot, files);
  const paths = snapshotPaths(cfg, branch, repoRoot);
  const hash = safeTreeHash(repoRoot, files);
  const plan = {
    mode: "snapshot-plan",
    repo_family_id: cfg.repo_family_id,
    source_branch: branch,
    source_commit: head,
    file_count: files.length,
    dirty_allowlisted: dirty,
    publish_eligible: dirty.length === 0 || !!headOnly,
    safe_tree_hash: hash,
    snapshot_dir: paths.snapshotDir,
    source_id: paths.sourceId,
  };
  if (!quiet) console.log(JSON.stringify(plan, null, 2));
  return plan;
}

function cmdSnapshotApply(repoRoot, headOnly) {
  const plan = cmdSnapshotPlan(repoRoot, headOnly, { quiet: true });
  if (!plan.publish_eligible) {
    die(
      "BLOCKED_DIRTY: allowlisted paths are dirty. Commit first or pass --head-only with Owner HEAD_ONLY_CONFIRMED.",
    );
  }
  const cfg = loadSources(repoRoot);
  const files = listCommittedAllowlist(repoRoot, cfg);
  const paths = snapshotPaths(cfg, plan.source_branch, repoRoot);
  ensureSnapshotRepo(paths.snapshotDir);

  // Remove previous allowlisted tracked files except .git and SOURCE.yaml
  const existing = existsSync(paths.snapshotDir)
    ? sh(["git", "-C", paths.snapshotDir, "ls-files"], { allowFail: true })
        .split(/\r?\n/)
        .filter(Boolean)
    : [];
  for (const f of existing) {
    if (f === "SOURCE.yaml") continue;
    const abs = join(paths.snapshotDir, f);
    if (existsSync(abs)) rmSync(abs, { force: true });
  }

  for (const f of files) {
    const r = gitShow(repoRoot, `HEAD:${f}`);
    if (r.status !== 0) continue;
    const dest = join(paths.snapshotDir, f);
    mkdirSync(dirname(dest), { recursive: true });
    writeFileSync(dest, r.stdout);
  }

  writeSourceYaml(paths.snapshotDir, {
    repo_family_id: cfg.repo_family_id,
    branch_id: paths.branchId,
    source_repo: repoRoot,
    source_branch: plan.source_branch,
    source_commit: plan.source_commit,
    safe_tree_hash: plan.safe_tree_hash,
    published_at_utc: new Date().toISOString(),
  });

  sh(["git", "add", "-A"], { cwd: paths.snapshotDir });
  const diff = sh(["git", "status", "--porcelain"], { cwd: paths.snapshotDir });
  if (!diff) {
    console.log(
      JSON.stringify({
        status: "CURRENT_NO_SAFE_DELTA",
        snapshot_dir: paths.snapshotDir,
        source_id: paths.sourceId,
        index_status: "UNKNOWN",
      }, null, 2),
    );
    return;
  }
  sh(
    [
      "git",
      "commit",
      "-m",
      `opsx-snapshot ${cfg.repo_family_id}/${paths.branchId} @ ${plan.source_commit.slice(0, 12)}`,
    ],
    { cwd: paths.snapshotDir },
  );
  const snapHead = sh(["git", "rev-parse", "HEAD"], { cwd: paths.snapshotDir });
  // optional push if remote exists — pushed only on exit 0 (allowFail must not imply success)
  const remotes = sh(["git", "remote"], { cwd: paths.snapshotDir, allowFail: true });
  let pushed = false;
  if (remotes.split(/\r?\n/).filter(Boolean).length) {
    const push = spawnSync("git", ["push"], {
      encoding: "utf8",
      cwd: paths.snapshotDir,
      maxBuffer: 64 * 1024 * 1024,
    });
    pushed = (push.status ?? 1) === 0;
  }
  console.log(
    JSON.stringify(
      {
        status: "SNAPSHOT_UPDATED",
        snapshot_dir: paths.snapshotDir,
        source_id: paths.sourceId,
        snapshot_head: snapHead,
        pushed,
        index_status: "STALE",
        next_action: "/opsx-meta-update-index",
      },
      null,
      2,
    ),
  );
}

function ensureCatalog(cfg, repoRoot = PROJECT_ROOT) {
  const paths = snapshotPaths(cfg, "main", repoRoot);
  mkdirSync(paths.catalogDir, { recursive: true });
  if (!existsSync(join(paths.catalogDir, ".git"))) {
    sh(["git", "init"], { cwd: paths.catalogDir });
    sh(["git", "config", "user.email", "opsx-central@local"], {
      cwd: paths.catalogDir,
    });
    sh(["git", "config", "user.name", "OPSX Catalog"], { cwd: paths.catalogDir });
  }
  for (const d of ["by-repo", "by-command", "by-hash", "discoveries"]) {
    mkdirSync(join(paths.catalogDir, d), { recursive: true });
  }
  const statePath = join(paths.catalogDir, "index-state.yaml");
  if (!existsSync(statePath)) {
    writeFileSync(statePath, "schema_version: 1\nsources: {}\n", "utf8");
  }
  const occ = join(paths.catalogDir, "occurrences.ndjson");
  if (!existsSync(occ)) writeFileSync(occ, "", "utf8");
  const sourcesReg = join(paths.catalogDir, "sources.yaml");
  if (!existsSync(sourcesReg)) {
    writeFileSync(
      sourcesReg,
      `schema_version: 1\nrepo_family_id: ${cfg.repo_family_id}\n`,
      "utf8",
    );
  }
  return paths.catalogDir;
}

function loadIndexState(catalogDir) {
  const p = join(catalogDir, "index-state.yaml");
  const raw = readFileSync(p, "utf8");
  // very small parser for sources map
  const state = { schema_version: 1, sources: {} };
  let cur = null;
  for (const line of raw.split(/\r?\n/)) {
    const m = line.match(/^  ([^:]+):\s*$/);
    if (m) {
      cur = m[1];
      state.sources[cur] = {};
      continue;
    }
    const kv = line.match(/^    ([^:]+):\s*(.*)$/);
    if (kv && cur) state.sources[cur][kv[1]] = coerce(kv[2]);
  }
  return state;
}

function saveIndexState(catalogDir, state) {
  const lines = ["schema_version: 1", "sources:"];
  for (const [id, row] of Object.entries(state.sources || {}).sort()) {
    lines.push(`  ${id}:`);
    for (const [k, v] of Object.entries(row)) {
      lines.push(`    ${k}: ${v}`);
    }
  }
  writeFileSync(join(catalogDir, "index-state.yaml"), lines.join("\n") + "\n", "utf8");
}

function loadOccurrences(catalogDir) {
  const p = join(catalogDir, "occurrences.ndjson");
  const text = readFileSync(p, "utf8");
  const map = new Map();
  for (const line of text.split(/\r?\n/).filter(Boolean)) {
    const row = JSON.parse(line);
    map.set(`${row.SOURCE_ID}::${row.COMMAND_PATH}`, row);
  }
  return map;
}

function saveOccurrences(catalogDir, map) {
  const rows = [...map.values()].sort((a, b) =>
    `${a.SOURCE_ID}:${a.COMMAND_PATH}`.localeCompare(
      `${b.SOURCE_ID}:${b.COMMAND_PATH}`,
    ),
  );
  writeFileSync(
    join(catalogDir, "occurrences.ndjson"),
    rows.map((r) => JSON.stringify(r)).join("\n") + (rows.length ? "\n" : ""),
    "utf8",
  );
}

function regenerateViews(catalogDir, map) {
  const byRepo = {};
  const byCommand = {};
  const byHash = {};
  for (const row of map.values()) {
    (byRepo[row.SOURCE_ID] ||= []).push(row);
    (byCommand[row.COMPONENT_ID] ||= []).push(row);
    (byHash[row.CANONICAL_BODY_HASH] ||= []).push(row);
  }
  // clear directories
  for (const d of ["by-repo", "by-command", "by-hash"]) {
    const dir = join(catalogDir, d);
    for (const f of readdirSync(dir)) {
      rmSync(join(dir, f), { force: true });
    }
  }
  for (const [id, rows] of Object.entries(byRepo)) {
    const safe = id.replace(/[\\/]/g, "__");
    writeFileSync(
      join(catalogDir, "by-repo", `${safe}.json`),
      JSON.stringify({ source_id: id, commands: rows }, null, 2) + "\n",
    );
  }
  for (const [id, rows] of Object.entries(byCommand)) {
    const safe = id.replace(/[\\/]/g, "__");
    writeFileSync(
      join(catalogDir, "by-command", `${safe}.json`),
      JSON.stringify({ component_id: id, occurrences: rows }, null, 2) + "\n",
    );
  }
  for (const [hash, rows] of Object.entries(byHash)) {
    writeFileSync(
      join(catalogDir, "by-hash", `${hash}.json`),
      JSON.stringify({ canonical_body_hash: hash, occurrences: rows }, null, 2) +
        "\n",
    );
  }
}

function listSnapshotSources(cfg, repoRoot = PROJECT_ROOT) {
  const root = resolve(repoRoot, cfg.central_root, cfg.sources_relpath || "sources");
  if (!existsSync(root)) return [];
  const out = [];
  for (const family of readdirSync(root)) {
    const famDir = join(root, family);
    if (!statSync(famDir).isDirectory()) continue;
    for (const branch of readdirSync(famDir)) {
      const snap = join(famDir, branch);
      if (!existsSync(join(snap, ".git"))) continue;
      out.push({
        source_id: `${family}/${branch}`,
        snapshot_dir: snap,
      });
    }
  }
  return out;
}

function commitStructureHash(sourceId, state, occMap, signals, prevPaths) {
  const prevHash = state.sources[sourceId]?.structure_hash || null;
  const nextPaths = pathsForSource(occMap, sourceId);
  const nextHash = structureHashFromPaths(nextPaths);
  if (prevHash && prevHash !== nextHash) {
    const diff = pathSetDiff(prevPaths || [], nextPaths);
    signals.push({
      kind: "STRUCTURE_CHANGED",
      source_id: sourceId,
      previous_structure_hash: prevHash,
      structure_hash: nextHash,
      added_paths: diff.added_paths,
      removed_paths: diff.removed_paths,
    });
  }
  const row = state.sources[sourceId] || {};
  row.structure_hash = nextHash;
  state.sources[sourceId] = row;
  return nextHash;
}

function indexOneSource(catalogDir, source, state, occMap, signals) {
  const head = sh(["git", "-C", source.snapshot_dir, "rev-parse", "HEAD"]);
  const prev = state.sources[source.source_id]?.last_indexed_commit;
  const prevPaths = pathsForSource(occMap, source.source_id);
  if (prev === head) {
    // No tree reads; backfill STRUCTURE_HASH from occurrence path set if missing.
    const structure_hash = commitStructureHash(
      source.source_id,
      state,
      occMap,
      signals,
      prevPaths,
    );
    if (!state.sources[source.source_id].last_indexed_commit) {
      state.sources[source.source_id].last_indexed_commit = head;
    }
    if (!state.sources[source.source_id].snapshot_dir) {
      state.sources[source.source_id].snapshot_dir = source.snapshot_dir.replace(
        /\\/g,
        "/",
      );
    }
    return {
      status: "UNCHANGED",
      source_id: source.source_id,
      head,
      structure_hash,
    };
  }
  let changedPaths = [];
  if (!prev) {
    changedPaths = sh([
      "git",
      "-C",
      source.snapshot_dir,
      "ls-tree",
      "-r",
      "--name-only",
      "HEAD",
    ])
      .split(/\r?\n/)
      .filter((p) => p.startsWith(".cursor/commands/opsx-") && p.endsWith(".md"));
  } else {
    const ancestor = sh(
      ["git", "-C", source.snapshot_dir, "merge-base", "--is-ancestor", prev, head],
      { allowFail: true },
    );
    // merge-base --is-ancestor returns status
    const ok = spawnSync(
      "git",
      ["-C", source.snapshot_dir, "merge-base", "--is-ancestor", prev, head],
    ).status === 0;
    if (!ok) {
      changedPaths = sh([
        "git",
        "-C",
        source.snapshot_dir,
        "ls-tree",
        "-r",
        "--name-only",
        "HEAD",
      ])
        .split(/\r?\n/)
        .filter((p) => p.startsWith(".cursor/commands/opsx-") && p.endsWith(".md"));
      // drop old occurrences for source
      for (const key of [...occMap.keys()]) {
        if (key.startsWith(source.source_id + "::")) occMap.delete(key);
      }
    } else {
      const diff = sh([
        "git",
        "-C",
        source.snapshot_dir,
        "diff",
        "--name-status",
        `${prev}..${head}`,
      ]);
      for (const line of diff.split(/\r?\n/).filter(Boolean)) {
        const [status, ...rest] = line.split(/\t/);
        const path = rest[rest.length - 1];
        if (!path.startsWith(".cursor/commands/opsx-") || !path.endsWith(".md")) {
          continue;
        }
        if (status.startsWith("D")) {
          occMap.delete(`${source.source_id}::${path}`);
          signals.push({ kind: "COMMAND_REMOVED", source_id: source.source_id, path });
        } else {
          changedPaths.push(path);
        }
      }
    }
  }

  for (const path of changedPaths) {
    const r = gitShow(source.snapshot_dir, `HEAD:${path}`);
    if (r.status !== 0) continue;
    const meta = commandMetaFromFile(path, r.stdout);
    const row = {
      OCCURRENCE_ID: sha256(Buffer.from(`${source.source_id}:${path}:${meta.full_file_hash}`)).slice(0, 16),
      SOURCE_ID: source.source_id,
      COMPONENT_ID: meta.component_id || path.split("/").pop().replace(/\.md$/, ""),
      COMMAND_PATH: path,
      FULL_FILE_HASH: meta.full_file_hash,
      CANONICAL_BODY_HASH: meta.canonical_body_hash,
      CONTRACT_HASH: meta.contract_hash,
      COMPONENT_VERSION: meta.component_version,
      ALIASES: meta.aliases,
      PURPOSE: meta.purpose,
      TAGS: meta.tags,
      SNAPSHOT_HEAD: head,
    };
    const key = `${source.source_id}::${path}`;
    const prevRow = occMap.get(key);
    occMap.set(key, row);
    signals.push({
      kind: prevRow ? "NEW_VARIANT" : "NEW_COMPONENT",
      source_id: source.source_id,
      component_id: row.COMPONENT_ID,
      path,
    });
  }

  state.sources[source.source_id] = {
    ...(state.sources[source.source_id] || {}),
    last_indexed_commit: head,
    snapshot_dir: source.snapshot_dir.replace(/\\/g, "/"),
  };
  const structure_hash = commitStructureHash(
    source.source_id,
    state,
    occMap,
    signals,
    prevPaths,
  );
  return {
    status: "INDEXED",
    source_id: source.source_id,
    head,
    changed: changedPaths.length,
    structure_hash,
  };
}

function cmdIndexPlan(repoRoot = PROJECT_ROOT) {
  const cfg = loadSources(repoRoot);
  const catalogDir = ensureCatalog(cfg, repoRoot);
  const state = loadIndexState(catalogDir);
  const sources = listSnapshotSources(cfg, repoRoot);
  const plan = sources.map((s) => {
    const head = sh(["git", "-C", s.snapshot_dir, "rev-parse", "HEAD"]);
    const prev = state.sources[s.source_id]?.last_indexed_commit || null;
    return {
      source_id: s.source_id,
      head,
      last_indexed_commit: prev,
      structure_hash: state.sources[s.source_id]?.structure_hash || null,
      status: prev === head ? "UNCHANGED" : "NEEDS_INDEX",
    };
  });
  console.log(JSON.stringify({ mode: "index-plan", catalog_dir: catalogDir, sources: plan }, null, 2));
}

function cmdIndexApply(repoRoot = PROJECT_ROOT) {
  const cfg = loadSources(repoRoot);
  const catalogDir = ensureCatalog(cfg, repoRoot);
  const state = loadIndexState(catalogDir);
  const occMap = loadOccurrences(catalogDir);
  const signals = [];
  const results = [];
  for (const s of listSnapshotSources(cfg, repoRoot)) {
    results.push(indexOneSource(catalogDir, s, state, occMap, signals));
  }
  saveOccurrences(catalogDir, occMap);
  regenerateViews(catalogDir, occMap);
  saveIndexState(catalogDir, state);
  if (signals.length) {
    writeFileSync(
      join(catalogDir, "discoveries", `${Date.now()}.json`),
      JSON.stringify({ signals }, null, 2) + "\n",
    );
  }
  sh(["git", "add", "-A"], { cwd: catalogDir });
  const dirty = sh(["git", "status", "--porcelain"], { cwd: catalogDir });
  if (dirty) {
    sh(["git", "commit", "-m", "opsx-index: incremental update"], {
      cwd: catalogDir,
    });
  }
  const head = sh(["git", "-C", catalogDir, "rev-parse", "HEAD"]);
  console.log(
    JSON.stringify(
      {
        status: "INDEX_UPDATED",
        catalog_dir: catalogDir,
        catalog_head: head,
        results,
        signal_count: signals.length,
      },
      null,
      2,
    ),
  );
}

function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];
  const repoIdx = args.indexOf("--repo");
  const repoRoot = repoIdx >= 0 ? resolve(args[repoIdx + 1]) : PROJECT_ROOT;
  const headOnly = args.includes("--head-only");
  if (cmd === "snapshot-plan") return void cmdSnapshotPlan(repoRoot, headOnly);
  if (cmd === "snapshot-apply") return void cmdSnapshotApply(repoRoot, headOnly);
  if (cmd === "index-plan") return void cmdIndexPlan(repoRoot);
  if (cmd === "index-apply") return void cmdIndexApply(repoRoot);
  die(
    "usage: node .opsx/tools/opsx-central-catalog.mjs <snapshot-plan|snapshot-apply|index-plan|index-apply> [--repo <path>] [--head-only]",
  );
}

main();
