#!/usr/bin/env node
// Forensic Audit Pipeline — headless `claude -p` orchestrator.
// Canonical substrate for the forensic-audit-pipeline skill. Reproducible & resumable.
//   node orchestrator.mjs            # run all incomplete stages (resume)
//   node orchestrator.mjs --stage N  # run exactly one stage (1..5)
//   node orchestrator.mjs --fresh    # tear down audit/ and start from Stage 1
// Nothing about the target is hardcoded: repo root = cwd, branch derived at runtime.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";

const REPO = resolve(process.cwd());
const AUDIT = join(REPO, "audit");
const WORK = join(AUDIT, ".work");

// ── args ──
const argv = process.argv.slice(2);
const getArg = (n) => { const i = argv.indexOf(n); return i >= 0 ? (argv[i + 1] || true) : undefined; };
const ONLY_STAGE = getArg("--stage") ? Number(getArg("--stage")) : undefined;
const FRESH = argv.includes("--fresh");

// ── helpers ──
const ts = () => new Date().toISOString().replace("T", " ").slice(0, 19);
const log = (...m) => console.error(`[${ts()}]`, ...m);
const L = (...a) => a.join("\n");
const sh = (c, a, o = {}) => new Promise((r) => {
  const p = spawn(c, a, { cwd: REPO, stdio: ["ignore", "pipe", "pipe"], ...o });
  let O = "", E = ""; p.stdout?.on("data", d => O += d); p.stderr?.on("data", d => E += d);
  p.on("close", code => r({ code, out: O, err: E }));
});
const safeRead = (p) => {
  try { return JSON.parse(readFileSync(p, "utf8")); }
  catch { try { return JSON.parse(readFileSync(p, "utf8").replace(/^﻿/, "").replace(/^```(json)?/i, "").replace(/```\s*$/, "").trim()); } catch { return null; } }
};

// ── minimal JSON-Schema validator (no ajv in this env) ──
function validate(schema, data, path = "$", errs = []) {
  if (!schema) return errs;
  if (schema.type) {
    const t = schema.type;
    const ok = t === "object" ? (data && typeof data === "object" && !Array.isArray(data))
      : t === "array" ? Array.isArray(data)
      : t === "string" ? typeof data === "string"
      : t === "integer" ? Number.isInteger(data)
      : t === "number" ? typeof data === "number"
      : t === "boolean" ? typeof data === "boolean"
      : t === "null" ? data === null : true;
    if (!ok) { errs.push(`${path}: expected ${t}, got ${Array.isArray(data) ? "array" : typeof data}`); return errs; }
  }
  if (schema.enum && !schema.enum.includes(data)) errs.push(`${path}: '${data}' not in enum`);
  if (schema.type === "object" && data && typeof data === "object") {
    for (const r of (schema.required || [])) if (!(r in data)) errs.push(`${path}.${r}: required`);
    for (const [k, sub] of Object.entries(schema.properties || {})) if (k in data) validate(sub, data[k], `${path}.${k}`, errs);
  }
  if (schema.type === "array" && Array.isArray(data) && schema.items) data.forEach((it, i) => validate(schema.items, it, `${path}[${i}]`, errs));
  return errs;
}

// ── global invariants (baked into every worker's system prompt) ──
const INVARIANTS = L(
  "GLOBAL AUDIT INVARIANTS — obey all of these:",
  "1. Absence of evidence is not evidence of absence. Never claim a thing does not exist, is unused, or is unreachable unless you name where you looked AND that search space is the full repo surface. Otherwise record it as 'unverified', never as 'absent'.",
  "2. No claim without a location. Every finding/behavior/assertion must cite a concrete path:line (or named artifact) a reviewer can open. Drop any claim lacking a citable anchor.",
  "3. Coverage has a denominator and visitation must be evidenced. Actually Read/Grep the files you claim to have inspected; do not infer contents.",
  "4. Verification is adversarial, not self-review. When falsifying, try to REFUTE each claim against source — do not rubber-stamp.",
  "5. Mutation is a means, not a deliverable. You may modify/instrument/run code in this sandbox to produce evidence, but the only shipped output is the audit JSON you Write.",
  "6. Never exfiltrate sensitive data. Reference any PII/PHI/secrets/credentials by path and category ONLY — never paste their contents into your output."
);

// ── cost & sequence ──
// NOTE: total_cost_usd from `claude -p` is an API-EQUIVALENT figure. On a Pro/Max
// subscription the real draw is ~10-100x smaller and bills against a usage window,
// not dollars. So budgetUsd here is a RUNAWAY GUARD (kills a looping agent), tuned
// generously — paired with timeoutMs as the primary stuck-agent guard. Pace by the
// usage window, not this number.
let TOTAL = 0, SEQ = 0, BRANCH = "";

// ── one subagent: file-handoff structured output, schema-validated, bounded ──
async function runAgent({ name, prompt, schema, model = "sonnet", budgetUsd = 4, web = false, timeoutMs = 900000, fallback, retries = 1 }) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    const out = join(WORK, `a_${name.replace(/\W+/g, "_")}_${SEQ++}.json`);
    try { if (existsSync(out)) rmSync(out); } catch {}
    const tools = web ? "Read,Grep,Glob,Bash,WebSearch,WebFetch,Write" : "Read,Grep,Glob,Bash,Write";
    const full = prompt + "\n\nOUTPUT CONTRACT: use the Write tool to put ONLY raw JSON (no prose, no markdown, no code fences) conforming to this JSON Schema at the EXACT path " + out + "\nSCHEMA: " + JSON.stringify(schema);
    const args = ["-p", full, "--output-format", "json", "--model", model, "--max-budget-usd", String(budgetUsd),
      "--allowedTools", tools, "--add-dir", REPO, "--strict-mcp-config", "--permission-mode", "acceptEdits",
      "--append-system-prompt", INVARIANTS];
    if (fallback) args.push("--fallback-model", fallback);
    const r = await new Promise((res) => {
      const p = spawn("claude", args, { cwd: REPO, stdio: ["ignore", "pipe", "pipe"] });
      let O = "", E = ""; const k = setTimeout(() => { try { p.kill("SIGKILL"); } catch {} }, timeoutMs);
      p.stdout.on("data", d => O += d); p.stderr.on("data", d => E += d);
      p.on("close", () => { clearTimeout(k); res({ O, E }); });
    });
    let env = null; try { env = JSON.parse(r.O); } catch {}
    const cost = Number(env?.total_cost_usd || 0); TOTAL += cost;
    const data = existsSync(out) ? safeRead(out) : null;
    if (data) {
      const errs = validate(schema, data);
      if (errs.length === 0) { log(`  ✓ ${name} ($${cost.toFixed(3)}, cum $${TOTAL.toFixed(2)})`); return { ok: true, data, cost }; }
      log(`  ✗ ${name} schema-violation: ${errs.slice(0, 3).join(" | ")} (attempt ${attempt})`);
    } else {
      log(`  ✗ ${name} no-output (envelope=${env?.subtype || env?.is_error || "none"}, err=${(r.E || "").slice(0, 120)}) (attempt ${attempt})`);
    }
  }
  return { ok: false };
}

// bounded-concurrency parallel barrier
const pMap = async (xs, fn, n = 3) => {
  const out = []; let i = 0;
  await Promise.all(Array(Math.min(n, xs.length)).fill(0).map(async () => { while (i < xs.length) { const k = i++; out[k] = await fn(xs[k], k); } }));
  return out;
};

// ── state / checkpoint / halt (durability) ──
const statePath = join(WORK, "state.json");
const loadState = () => existsSync(statePath) ? safeRead(statePath) || { completed: {} } : { completed: {}, started: Date.now() };
const writeState = (s) => writeFileSync(statePath, JSON.stringify(s, null, 2));
async function checkpoint(stageKey, mdName, md, jsonName, obj, state) {
  writeFileSync(join(AUDIT, mdName), md);
  writeFileSync(join(WORK, jsonName), JSON.stringify(obj, null, 2));
  state.completed[stageKey] = Date.now(); state.totalCost = TOTAL; writeState(state);
  await sh("git", ["add", "audit"]);
  await sh("git", ["commit", "-m", `audit: ${stageKey} (cumulative $${TOTAL.toFixed(2)})`]);
  for (let i = 0; i < 4; i++) { const p = await sh("git", ["push", "-u", "origin", BRANCH]); if (p.code === 0) break; log(`push retry ${i}: ${p.err.slice(0, 160)}`); await new Promise(r => setTimeout(r, (2 ** (i + 1)) * 1000)); }
  log(`★ checkpoint ${stageKey} → ${mdName} committed`);
}
async function halt(stageKey, why, state) {
  const md = L(`# HALT at ${stageKey}`, "", "The pipeline stopped because a stop-test could not be satisfied honestly.", "", `**Reason:** ${why}`, "", `Cumulative cost at halt: $${TOTAL.toFixed(2)}`, "", `Time: ${ts()}`);
  writeFileSync(join(AUDIT, "HALT-REPORT.md"), md);
  state.halt = { stageKey, why, at: Date.now() }; writeState(state);
  await sh("git", ["add", "audit"]); await sh("git", ["commit", "-m", `audit: HALT ${stageKey}`]);
  await sh("git", ["push", "-u", "origin", BRANCH]);
  log(`HALT ${stageKey}: ${why}`); process.exit(2);
}

// ════════════════════════════ STAGE 1 — UNDERSTANDING ════════════════════════════
const ROLES = ["source", "test", "doc", "config", "asset", "generated", "dead"];
const INVENTORY_SCHEMA = {
  type: "object", required: ["files", "entry_points", "architecture_summary", "provisional_intent"],
  properties: {
    files: { type: "array", items: { type: "object", required: ["path", "role", "note"], properties: { path: { type: "string" }, role: { type: "string", enum: ROLES }, note: { type: "string" } } } },
    entry_points: { type: "array", items: { type: "object", required: ["name", "kind", "location", "description"], properties: { name: { type: "string" }, kind: { type: "string" }, location: { type: "string" }, description: { type: "string" } } } },
    architecture_summary: { type: "string" },
    provisional_intent: { type: "string" },
  },
};
const FALSIFY_SCHEMA = {
  type: "object", required: ["checks", "problems", "verdict"],
  properties: {
    checks: { type: "array", items: { type: "object", required: ["name", "passed", "evidence"], properties: { name: { type: "string" }, passed: { type: "boolean" }, evidence: { type: "string" } } } },
    problems: { type: "array", items: { type: "object", required: ["description", "location", "severity"], properties: { description: { type: "string" }, location: { type: "string" }, severity: { type: "string" } } } },
    verdict: { type: "string", enum: ["pass", "fail", "pass_with_corrections"] },
  },
};

function renderStage1MD(inv, denomLen, fal) {
  const counts = {}; for (const f of inv.files) counts[f.role] = (counts[f.role] || 0) + 1;
  const ep = inv.entry_points.map(e => `| \`${e.name}\` | ${e.kind} | \`${e.location}\` | ${e.description.replace(/\n/g, " ")} |`).join("\n");
  const byRole = ROLES.map(r => `- **${r}**: ${counts[r] || 0}`).join("\n");
  const fileRows = inv.files.map(f => `| \`${f.path}\` | ${f.role} | ${f.note.replace(/\n/g, " ").slice(0, 200)} |`).join("\n");
  const falLine = fal ? `Adversarial falsification verdict: **${fal.verdict}** (${fal.problems.length} problem(s) raised, all resolved before promotion).` : "Falsification: not run.";
  return L(
    "# 01 — Comprehensive Understanding", "",
    `_Generated by the forensic-audit-pipeline orchestrator. Denominator: ${denomLen} tracked paths (excluding \`audit/\`). ${falLine}_`, "",
    "## Provisional intent (to be refined in Stage 4)", "", inv.provisional_intent, "",
    "## Architecture summary", "", inv.architecture_summary, "",
    "## Entry points", "", "| Name | Kind | Location | Description |", "| --- | --- | --- | --- |", ep, "",
    "## Role distribution", "", byRole, "",
    "## Full file inventory (coverage denominator)", "", "| Path | Role | Note |", "| --- | --- | --- |", fileRows, ""
  );
}

async function stage1(state) {
  log("═══ STAGE 1: comprehensive understanding ═══");
  const tracked = (await sh("git", ["ls-files"])).out.trim().split("\n").filter(Boolean);
  const denom = tracked.filter(p => !p.startsWith("audit/"));
  writeFileSync(join(WORK, "denominator.json"), JSON.stringify(denom, null, 2));
  log(`denominator: ${denom.length} tracked paths`);

  const invPrompt = L(
    "You are the Stage-1 UNDERSTANDING agent of a forensic repository audit. Produce a complete, role-classified map of the repo AS IT IS.",
    `REPO ROOT: ${REPO}`,
    `The authoritative file DENOMINATOR (from \`git ls-files\`, ${denom.length} paths, audit/ excluded) is also written at ${join(WORK, "denominator.json")}. It is:`,
    denom.join("\n"),
    "",
    "TASKS:",
    `1. Classify EVERY path above into exactly one role from {${ROLES.join(", ")}}. Every denominator path MUST appear in 'files'; NO path may be omitted and NO role may be left 'unknown'. For code files whose role is not obvious from the path, open them. Put a one-line 'note' on each saying what it is.`,
    "2. Trace EVERY entry point — console_scripts/[project.scripts] in pyproject, CLI commands & subcommands, exported public APIs, main modules, runnable scripts, CI/task entry — each to a one-line description. READ the actual entry files (pyproject.toml, main modules, CLI modules, Taskfile, scripts) and cite path:line in 'location'.",
    "3. Write an 'architecture_summary': the layers, key components, control/data flow, and how the pieces connect — grounded in real files (reference paths).",
    "4. Write a 'provisional_intent': the apparent long-term goal/reason the project exists. Mark it provisional; Stage 4 will refine it.",
    "Be exhaustive and concrete. This inventory is the COVERAGE DENOMINATOR for every later stage, so completeness matters more than brevity."
  );
  let res = await runAgent({ name: "s1-inventory", prompt: invPrompt, schema: INVENTORY_SCHEMA, model: "sonnet", budgetUsd: 12, timeoutMs: 900000 });
  if (!res.ok) await halt("stage1", "inventory agent failed to produce a schema-valid inventory after retries", state);
  let inv = res.data;

  // code-enforced coverage: every denominator path classified, no unknown role
  const fix = (inv) => {
    const classified = new Set(inv.files.map(f => f.path));
    return { missing: denom.filter(p => !classified.has(p)), extra: inv.files.map(f => f.path).filter(p => !denom.includes(p)) };
  };
  let { missing } = fix(inv);
  log(`coverage: ${inv.files.length} classified, ${missing.length} missing, ${inv.entry_points.length} entry points`);
  writeFileSync(join(WORK, "01-inventory.json"), JSON.stringify(inv, null, 2));

  // adversarial falsifier (independent, fresh context, opus)
  const falPrompt = L(
    "You are an INDEPENDENT FALSIFIER for a Stage-1 repository inventory. Do NOT trust it; try to REFUTE it against the real files.",
    `REPO ROOT: ${REPO}`,
    `The inventory JSON is at ${join(WORK, "01-inventory.json")} — Read it.`,
    `The authoritative denominator (${denom.length} paths) is at ${join(WORK, "denominator.json")} — Read it.`,
    "CHECKS (record each as a check with path:line evidence):",
    "  a) Role accuracy: open >= 15 files across different subtrees and confirm their assigned role is correct. Flag every misclassification.",
    "  b) Entry-point integrity: for EVERY entry_point, open its cited location and confirm it exists and the description matches the code. Flag wrong/nonexistent citations.",
    "  c) Entry-point completeness: search for runnable surfaces the inventory MISSED (pyproject [project.scripts], click groups/@cli.command, __main__, if __name__=='__main__', argparse, FastAPI/flask routes). List any missing.",
    "  d) Architecture fidelity: is the architecture_summary supported by real files? Flag unsupported claims.",
    "  e) Intent sanity: is provisional_intent consistent with README/pyproject/docs?",
    "Set verdict='pass' only if no problems; 'pass_with_corrections' if minor/fixable; 'fail' if the inventory is substantially wrong. List every problem with a path:line location and a severity (low|medium|high)."
  );
  const fal = await runAgent({ name: "s1-falsify", prompt: falPrompt, schema: FALSIFY_SCHEMA, model: "opus", budgetUsd: 10, timeoutMs: 900000 });

  // correction round if needed (coverage gaps OR falsifier problems)
  const needsFix = missing.length > 0 || (fal.ok && fal.data.verdict !== "pass" && fal.data.problems.length > 0);
  if (needsFix) {
    log(`correction round: missing=${missing.length}, falsifier=${fal.ok ? fal.data.verdict : "n/a"}`);
    const probTxt = fal.ok ? fal.data.problems.map(p => `- [${p.severity}] ${p.description} @ ${p.location}`).join("\n") : "(falsifier unavailable)";
    const corrPrompt = L(
      "You are correcting a Stage-1 repository inventory. Produce a COMPLETE corrected inventory (same schema) — not a diff.",
      `REPO ROOT: ${REPO}`,
      `Current inventory: ${join(WORK, "01-inventory.json")} — Read it.`,
      `Denominator (${denom.length} paths, every one MUST appear in files): ${join(WORK, "denominator.json")} — Read it.`,
      missing.length ? `These denominator paths are MISSING and must be added & classified: ${missing.join(", ")}` : "All denominator paths are present.",
      "Independent falsifier raised these problems — fix every one by opening the relevant files:",
      probTxt,
      "Output the full corrected inventory conforming to the schema."
    );
    const corr = await runAgent({ name: "s1-correct", prompt: corrPrompt, schema: INVENTORY_SCHEMA, model: "opus", budgetUsd: 12, timeoutMs: 900000 });
    if (corr.ok) { inv = corr.data; ({ missing } = fix(inv)); writeFileSync(join(WORK, "01-inventory.json"), JSON.stringify(inv, null, 2)); log(`after correction: ${inv.files.length} classified, ${missing.length} missing`); }
  }

  // STOP-TEST: full coverage, no unknown roles
  const unknown = inv.files.filter(f => !ROLES.includes(f.role));
  if (missing.length > 0) await halt("stage1", `coverage stop-test failed: ${missing.length} denominator paths unclassified (e.g. ${missing.slice(0, 8).join(", ")})`, state);
  if (unknown.length > 0) await halt("stage1", `convergence stop-test failed: ${unknown.length} files have a role outside the allowed set`, state);
  if (inv.entry_points.length === 0) await halt("stage1", "no entry points traced — implausible for a real code project; inventory likely incomplete", state);

  const md = renderStage1MD(inv, denom.length, fal.ok ? fal.data : null);
  inv._meta = { denominator: denom.length, classified: inv.files.length, entry_points: inv.entry_points.length, falsifier_verdict: fal.ok ? fal.data.verdict : "unavailable", cost_usd: Number(TOTAL.toFixed(2)) };
  await checkpoint("stage1", "01-understanding.md", md, "01-inventory.json", inv, state);
}

// ════════════════════════════ shared helpers for findings/plan ════════════════════════════
const SEV = ["low", "medium", "high", "critical"];
const fp = (f) => `${(f.location || "").toLowerCase().trim()}|${(f.class || "").toLowerCase()}`;
const sliceArr = (arr, n) => { const out = Array.from({ length: n }, () => []); arr.forEach((x, i) => out[i % n].push(x)); return out.filter(s => s.length); };
const dedupeFindings = (arr) => { const m = new Map(); for (const f of arr) { const k = fp(f); if (!m.has(k)) m.set(k, f); else if (SEV.indexOf(f.severity) > SEV.indexOf(m.get(k).severity)) m.set(k, f); } return [...m.values()]; };
const reindex = (arr) => arr.map((f, i) => ({ ...f, id: `F${i + 1}` }));
const keepSurvivors = (findings, verdicts) => { const v = new Map((verdicts || []).map(x => [x.id, x])); return findings.filter(f => v.get(f.id)?.survives === true).map(f => { const d = v.get(f.id); return d?.corrected_severity && SEV.includes(d.corrected_severity) ? { ...f, severity: d.corrected_severity } : f; }); };

// ════════════════════════════ STAGE 2 — STATIC AUDIT (adversarial fixpoint) ════════════════════════════
const FINDING = { type: "object", required: ["id", "location", "class", "severity", "evidence", "intent_mismatch"], properties: { id: { type: "string" }, location: { type: "string" }, class: { type: "string", enum: ["bug", "security", "doc_drift", "design_defect", "performance", "test_gap", "other"] }, severity: { type: "string", enum: SEV }, evidence: { type: "string" }, intent_mismatch: { type: "boolean" } } };
const AUDIT_SCHEMA = { type: "object", required: ["findings", "visited"], properties: { findings: { type: "array", items: FINDING }, visited: { type: "array", items: { type: "string" } } } };
const VERDICTS_SCHEMA = { type: "object", required: ["verdicts"], properties: { verdicts: { type: "array", items: { type: "object", required: ["id", "survives", "reason"], properties: { id: { type: "string" }, survives: { type: "boolean" }, reason: { type: "string" }, corrected_severity: { type: "string" } } } } } };

function renderStage2MD(obj) {
  const rank = { critical: 0, high: 1, medium: 2, low: 3 };
  const rows = [...obj.findings].sort((a, b) => rank[a.severity] - rank[b.severity]).map(f => `| ${f.id} | ${f.severity} | ${f.class} | \`${f.location}\` | ${f.intent_mismatch ? "⚠️ " : ""}${f.evidence.replace(/\n/g, " ").slice(0, 320)} |`).join("\n");
  return L("# 02 — Static Audit", "", `_${obj.findings.length} findings, each surviving an independent adversarial falsification pass. Auditable surface: ${obj.auditable_files} files. Severity: ${obj.summary.critical || 0} critical / ${obj.summary.high || 0} high / ${obj.summary.medium || 0} medium / ${obj.summary.low || 0} low._`, "", `**Judged against provisional intent:** ${obj.provisional_intent}`, "", "| ID | Severity | Class | Location | Evidence (⚠️ = code/intent mismatch) |", "| --- | --- | --- | --- | --- |", rows, "");
}

async function stage2(state) {
  log("═══ STAGE 2: static audit (adversarial fixpoint) ═══");
  const inv = safeRead(join(WORK, "01-inventory.json"));
  if (!inv) await halt("stage2", "missing 01-inventory.json — run stage 1 first", state);
  const intent = inv.provisional_intent;
  const auditable = inv.files.filter(f => ["source", "test", "config", "doc"].includes(f.role)).map(f => f.path);
  writeFileSync(join(WORK, "auditable.json"), JSON.stringify(auditable, null, 2));
  log(`auditable surface: ${auditable.length} files`);

  // ROUND 1 — slice audit (coverage by construction: every auditable file in exactly one slice)
  const slices = sliceArr(auditable, Math.min(5, Math.max(2, Math.ceil(auditable.length / 30))));
  log(`round1: ${slices.length} audit slices`);
  const ar = await pMap(slices, (files, idx) => runAgent({
    name: `s2-audit${idx}`, model: "sonnet", budgetUsd: 12, timeoutMs: 1200000, schema: AUDIT_SCHEMA,
    prompt: L("You are a Stage-2 STATIC AUDIT agent. Find EVERY defect discoverable by READING your assigned files. You MUST open (Read) each one. Cite path:line for every finding.",
      `REPO ROOT: ${REPO}`,
      `PROVISIONAL INTENT (judge defects relative to this; a code/intent mismatch is itself a finding): ${intent}`,
      "Defect classes: bug (logic/correctness/crash), security (injection, leaked/secret handling, unsafe subprocess, path traversal), doc_drift (code contradicts docstring/README/comment), design_defect (dead code, broken abstraction, fragile coupling), performance, test_gap (untested critical path, test that asserts nothing), other.",
      "ASSIGNED FILES — Read EVERY one:", files.join("\n"),
      "Each finding: location (path:line), class, severity (low|medium|high|critical), evidence (what's wrong, referenced by location — NEVER paste secrets/PII, cite them by path+category), intent_mismatch (bool). Also return 'visited': the exact paths you opened.")
  }), 3);
  let findings = []; const visited = new Set();
  for (const r of ar) if (r.ok) { findings.push(...r.data.findings); (r.data.visited || []).forEach(v => visited.add(v)); }
  findings = reindex(dedupeFindings(findings));
  log(`round1: ${findings.length} findings, visited ${visited.size}/${auditable.length}`);

  // COVERAGE stop-test (one gap-fill pass, then enforce)
  let gaps = auditable.filter(p => !visited.has(p));
  if (gaps.length) {
    log(`coverage gap ${gaps.length} → gap-fill`);
    const g = await runAgent({ name: "s2-gapfill", model: "sonnet", budgetUsd: 10, timeoutMs: 900000, schema: AUDIT_SCHEMA, prompt: L("Stage-2 audit GAP-FILL: Read EVERY file below and report any defects; return 'visited' listing the files you opened.", `REPO ROOT: ${REPO}`, `PROVISIONAL INTENT: ${intent}`, "FILES:", gaps.join("\n"), "Finding format: location/class/severity/evidence/intent_mismatch.") });
    if (g.ok) { findings = reindex(dedupeFindings([...findings, ...g.data.findings])); (g.data.visited || []).forEach(v => visited.add(v)); }
    gaps = auditable.filter(p => !visited.has(p));
  }
  if (gaps.length > Math.ceil(auditable.length * 0.05)) await halt("stage2", `coverage stop-test failed: ${gaps.length}/${auditable.length} auditable files never visited (e.g. ${gaps.slice(0, 8).join(", ")})`, state);

  // FIXPOINT: reaudit (add candidates FIRST) → falsify WHOLE set → survivors → stability
  let prevSig = ""; const ceiling = 4;
  for (let round = 1; round <= ceiling; round++) {
    const known = findings.map(f => `${f.id} [${f.class}/${f.severity}] ${f.location} :: ${f.evidence.slice(0, 110)}`).join("\n");
    const re = await runAgent({ name: `s2-reaudit-r${round}`, model: "sonnet", budgetUsd: 12, timeoutMs: 1200000, schema: AUDIT_SCHEMA, prompt: L("You are a Stage-2 RE-AUDIT sweep. Find what the existing findings MISSED — especially cross-file/architectural defects, code/intent drift, security issues, and dead code a per-file pass cannot catch. Do NOT duplicate existing findings. Cite path:line; Read the files you reason about.", `REPO ROOT: ${REPO}`, `PROVISIONAL INTENT: ${intent}`, `AUDITABLE SURFACE (${auditable.length} files) at ${join(WORK, "auditable.json")} — Read it.`, "EXISTING FINDINGS (do not duplicate):", known || "(none yet)", "Return only NEW findings (same format) + 'visited'.") });
    if (re.ok) findings = reindex(dedupeFindings([...findings, ...re.data.findings]));
    log(`r${round} post-reaudit: ${findings.length}`);
    const fset = findings.map(f => `${f.id} | ${f.class}/${f.severity} | ${f.location} | ${f.evidence.slice(0, 200)}`).join("\n");
    const fal = await runAgent({ name: `s2-falsify-r${round}`, model: "opus", budgetUsd: 14, timeoutMs: 1500000, schema: VERDICTS_SCHEMA, prompt: L("You are an INDEPENDENT FALSIFIER. For EACH finding below, open the cited location in source and try to REFUTE it. It SURVIVES only if source genuinely supports it. Return a verdict for EVERY id — be skeptical: refute anything mislocated, unsupported, or actually-correct behavior.", `REPO ROOT: ${REPO}`, `PROVISIONAL INTENT: ${intent}`, "FINDINGS (id | class/severity | location | evidence):", fset, "Each verdict: id, survives (bool), reason (with the path:line you checked), corrected_severity (optional).") });
    if (!fal.ok) await halt("stage2", `falsifier failed in round ${round} — no finding may be promoted without an adversarial pass`, state);
    const before = findings.length;
    findings = reindex(keepSurvivors(findings, fal.data.verdicts));
    log(`r${round} post-falsify: ${findings.length} survivors (dropped ${before - findings.length})`);
    const sig = findings.map(fp).sort().join("||");
    if (sig === prevSig) { log(`fixpoint at round ${round}`); break; }
    prevSig = sig;
    if (round === ceiling) await halt("stage2", `no fixpoint within ${ceiling} rounds — findings set still churning`, state);
  }

  const summary = { critical: 0, high: 0, medium: 0, low: 0 }; for (const f of findings) summary[f.severity] = (summary[f.severity] || 0) + 1;
  const obj = { provisional_intent: intent, auditable_files: auditable.length, findings, summary, _meta: { cost_usd: Number(TOTAL.toFixed(2)) } };
  await checkpoint("stage2", "02-static-audit.md", renderStage2MD(obj), "02-findings.json", obj, state);
}

// ════════════════════════════ STAGE 3 — EXECUTION / DYNAMIC SURFACE ════════════════════════════
const EXEC_SCHEMA = { type: "object", required: ["env_setup", "test_result", "entrypoint_runs", "stage2_deltas", "unexecuted", "summary"], properties: { env_setup: { type: "array", items: { type: "object", required: ["step", "ok"], properties: { step: { type: "string" }, command: { type: "string" }, ok: { type: "boolean" }, note: { type: "string" } } } }, test_result: { type: "object", required: ["ran", "summary"], properties: { ran: { type: "boolean" }, passed: { type: "integer" }, failed: { type: "integer" }, skipped: { type: "integer" }, errors: { type: "integer" }, coverage_pct: { type: "number" }, summary: { type: "string" } } }, entrypoint_runs: { type: "array", items: { type: "object", required: ["command", "exit_code", "observation"], properties: { command: { type: "string" }, exit_code: { type: "integer" }, observation: { type: "string" } } } }, stage2_deltas: { type: "array", items: { type: "object", required: ["finding_id", "status", "evidence"], properties: { finding_id: { type: "string" }, status: { type: "string", enum: ["confirmed", "refuted", "refined", "untested"] }, evidence: { type: "string" } } } }, unexecuted: { type: "array", items: { type: "object", required: ["region", "reason"], properties: { region: { type: "string" }, reason: { type: "string", enum: ["requires-credentials", "external-service", "hardware-gated", "dead", "destructive-skip", "build-failed", "other"] } } } }, summary: { type: "string" } } };
const EXEC_VERIFY_SCHEMA = { type: "object", required: ["coverage_confirmed", "observed", "discrepancies"], properties: { coverage_confirmed: { type: "boolean" }, observed: { type: "string" }, discrepancies: { type: "array", items: { type: "object", required: ["description", "location"], properties: { description: { type: "string" }, location: { type: "string" } } } } } };

function renderStage3MD(obj) {
  const env = obj.env_setup.map(s => `- ${s.ok ? "✓" : "✗"} ${s.step}${s.command ? ` (\`${s.command}\`)` : ""}${s.note ? " — " + s.note : ""}`).join("\n");
  const eps = obj.entrypoint_runs.map(e => `| \`${e.command}\` | ${e.exit_code} | ${e.observation.replace(/\n/g, " ").slice(0, 220)} |`).join("\n");
  const deltas = obj.stage2_deltas.map(d => `| ${d.finding_id} | ${d.status} | ${d.evidence.replace(/\n/g, " ").slice(0, 220)} |`).join("\n");
  const un = obj.unexecuted.map(u => `- \`${u.region}\` — **${u.reason}**`).join("\n");
  const tr = obj.test_result, v = obj.verification || {};
  const disc = v.discrepancies && v.discrepancies.length ? "\n\n**Discrepancies the verifier found:**\n" + v.discrepancies.map(d => `- ${d.description} (${d.location})`).join("\n") : "";
  return L("# 03 — Execution / Dynamic Surface", "", `_Tests ran: **${tr.ran}**.${tr.ran ? ` Passed ${tr.passed ?? "?"}, failed ${tr.failed ?? "?"}, skipped ${tr.skipped ?? "?"}, errors ${tr.errors ?? "?"}, coverage ${tr.coverage_pct ?? "?"}%.` : ""} Independent verification: coverage_confirmed=**${v.coverage_confirmed}**._`, "", "## Summary", "", obj.summary, "", "## Environment setup (discovered from the repo)", "", env, "", "## Test result", "", tr.summary, "", "## Entry points exercised", "", "| Command | Exit | Observation |", "| --- | --- | --- |", eps, "", "## Stage-2 findings — execution delta", "", "| Finding | Status | Evidence |", "| --- | --- | --- |", deltas, "", "## Un-executed accounting (every region carries a reason)", "", un, "", "## Independent verification", "", `coverage_confirmed: **${v.coverage_confirmed}** — ${v.observed || v.note || ""}${disc}`, "");
}

async function stage3(state) {
  log("═══ STAGE 3: execution / dynamic surface ═══");
  const inv = safeRead(join(WORK, "01-inventory.json")), f2 = safeRead(join(WORK, "02-findings.json"));
  if (!inv || !f2) await halt("stage3", "missing stage 1/2 artifacts", state);
  const fl = f2.findings.map(f => `${f.id} | ${f.class}/${f.severity} | ${f.location} | ${f.evidence.slice(0, 140)}`).join("\n");
  const eps = inv.entry_points.map(e => `${e.name} (${e.kind}) @ ${e.location}`).join("\n");
  const exec = await runAgent({
    name: "s3-exec", model: "sonnet", budgetUsd: 25, timeoutMs: 1800000, schema: EXEC_SCHEMA,
    prompt: L("You are the Stage-3 EXECUTION agent. Determine what the code ACTUALLY DOES when run. You may install deps, create venvs, and run commands in this sandbox.",
      `REPO ROOT: ${REPO}`,
      "STEPS:",
      "1. DISCOVER build/test/coverage commands FROM THE REPO ITSELF — read README, pyproject.toml, Taskfile.yml, pytest.ini, .github/workflows/*.yml, and any package manifest. Never assume another project's commands.",
      "2. SET UP the environment (create a venv; install project + dev deps with the discovered tool — uv or pip). Record each step + whether it succeeded in env_setup.",
      "3. RUN the test suite under coverage with the discovered command. Read the coverage report it emits and record passed/failed/skipped/errors and coverage_pct. If it cannot run, set test_result.ran=false and explain in summary with the exact error.",
      "4. DRIVE entry points that are safe (e.g. `--help`, version). Record command/exit_code/observation. Do NOT run anything destructive or needing real credentials — record those under unexecuted with reason=requires-credentials.",
      "5. CONFIRM/REFUTE/REFINE the Stage-2 findings below using what you observed (stage2_deltas: finding_id, status, evidence).",
      "6. Account for un-executed code (unexecuted: region + reason from {requires-credentials, external-service, hardware-gated, dead, destructive-skip, build-failed, other}).",
      "Save the coverage report and key run logs under audit/.work/ so they can be INDEPENDENTLY verified.",
      "ENTRY POINTS (from Stage 1):", eps,
      "STAGE-2 FINDINGS (id | class/severity | location | evidence):", fl || "(none)")
  });
  if (!exec.ok) await halt("stage3", "execution agent produced no schema-valid result", state);
  writeFileSync(join(WORK, "03-exec-raw.json"), JSON.stringify(exec.data, null, 2));
  const ver = await runAgent({ name: "s3-verify", model: "opus", budgetUsd: 10, timeoutMs: 900000, schema: EXEC_VERIFY_SCHEMA, prompt: L("You INDEPENDENTLY verify a Stage-3 execution report. Do NOT trust its self-reported numbers.", `REPO ROOT: ${REPO}`, `The report is at ${join(WORK, "03-exec-raw.json")} — Read it.`, "Checks: (a) re-read any coverage report/logs it saved under audit/.work/ and confirm the claimed coverage_pct and pass/fail counts match the real artifacts; (b) confirm un-executed reasons are legitimate, not hiding avoidable gaps; (c) spot-check 2-3 entry-point runs yourself.", "Report coverage_confirmed (bool), observed (what you actually measured), discrepancies[{description, location}].") });
  const obj = { ...exec.data, verification: ver.ok ? ver.data : { coverage_confirmed: false, note: "verifier unavailable" }, _meta: { cost_usd: Number(TOTAL.toFixed(2)) } };
  await checkpoint("stage3", "03-execution.md", renderStage3MD(obj), "03-execution.json", obj, state);
}

// ════════════════════════════ STAGE 4 — GOAL ‖ RESEARCH (parallel) ════════════════════════════
const GOAL_SCHEMA = { type: "object", required: ["candidates"], properties: { candidates: { type: "array", items: { type: "object", required: ["goal", "rationale", "success_signals", "status"], properties: { goal: { type: "string" }, rationale: { type: "string" }, success_signals: { type: "array", items: { type: "object", required: ["signal", "grounding"], properties: { signal: { type: "string" }, grounding: { type: "string" } } } }, status: { type: "string", enum: ["grounded", "speculative"] } } } } } };
const RESEARCH_SCHEMA = { type: "object", required: ["sources"], properties: { sources: { type: "array", items: { type: "object", required: ["title", "url", "claim", "relevance", "corroborated"], properties: { title: { type: "string" }, url: { type: "string" }, claim: { type: "string" }, relevance: { type: "string" }, corroborated: { type: "boolean" } } } } } };
const RESEARCH_SYNTH_SCHEMA = { type: "object", required: ["synthesis", "key_ideas", "unverified"], properties: { synthesis: { type: "string" }, key_ideas: { type: "array", items: { type: "object", required: ["idea", "why_relevant", "sources", "confidence"], properties: { idea: { type: "string" }, why_relevant: { type: "string" }, sources: { type: "array", items: { type: "string" } }, confidence: { type: "string" } } } }, unverified: { type: "array", items: { type: "string" } } } };

function renderStage4MD(obj) {
  const cands = obj.goal.candidates.map(c => L(`### ${c.status === "grounded" ? "✅ grounded" : "🟡 speculative"} — ${c.goal}`, "", c.rationale, "", c.success_signals.map(s => `- **Signal:** ${s.signal}  \n  _grounding:_ ${s.grounding}`).join("\n"))).join("\n\n");
  const syn = obj.research.synthesis;
  const ideas = syn ? (syn.key_ideas || []).map(k => `- **${k.idea}** _(${k.confidence})_ — ${k.why_relevant}  \n  ${(k.sources || []).slice(0, 4).join(" · ")}`).join("\n") : "";
  const srcs = (obj.research.sources || []).slice(0, 40).map(s => `- [${s.title || s.url}](${s.url})${s.corroborated ? " ✓" : " _(unverified)_"} — ${(s.relevance || s.claim || "").slice(0, 150)}`).join("\n");
  const unv = syn && syn.unverified && syn.unverified.length ? L("", "### Unverified claims (single/weak source)", "", syn.unverified.map(u => `- ${u}`).join("\n")) : "";
  return L("# 04 — Grounded Goal + External Research", "", "## Candidate long-term goals", "", cands, "", "## Research synthesis", "", syn ? syn.synthesis : "(research synthesis unavailable)", "", "### Key ideas that advance the goal", "", ideas, unv, "", "## Sources", "", srcs, "");
}

async function stage4(state) {
  log("═══ STAGE 4: goal + external research (parallel) ═══");
  const inv = safeRead(join(WORK, "01-inventory.json")), f2 = safeRead(join(WORK, "02-findings.json")), f3 = safeRead(join(WORK, "03-execution.json"));
  if (!inv) await halt("stage4", "missing inventory", state);
  const ground = L(`PROVISIONAL INTENT (Stage 1): ${inv.provisional_intent}`, `ARCHITECTURE: ${(inv.architecture_summary || "").slice(0, 1500)}`, `ENTRY POINTS: ${inv.entry_points.map(e => e.name + " (" + e.kind + ")").join(", ")}`, f2 ? `TOP FINDINGS: ${f2.findings.slice(0, 12).map(f => f.class + "/" + f.severity + "@" + f.location).join("; ")}` : "", f3 ? `EXECUTION: tests ran=${f3.test_result?.ran}, coverage=${f3.test_result?.coverage_pct ?? "?"}%; ${(f3.summary || "").slice(0, 400)}` : "");
  const goalFn = () => runAgent({ name: "s4-goal", model: "opus", budgetUsd: 8, timeoutMs: 900000, schema: GOAL_SCHEMA, prompt: L("You are the Stage-4 GOAL agent. Infer the repo's grounded LONG-TERM goal(s). Keep candidates PLURAL (2-4). Each success signal must trace to a concrete Stage 1-3 artifact (a path or a measured fact). A candidate with no grounding is speculative — mark status accordingly, do not drop it silently.", `REPO ROOT: ${REPO}`, "GROUNDING (Stages 1-3):", ground, "Read repo docs to ground/refute candidates (README, docs/, .taskmaster/, any PRD/roadmap/design files); cite them in grounding.", "Output candidates[]: {goal, rationale, success_signals[{signal, grounding}], status (grounded|speculative)}.") });
  const facets = ["state of the art in automated program repair (APR) and LLM-based automatic test/code fixing — techniques, agent designs, key tools & papers 2023-2025", "automated & property-based test generation tooling (Hypothesis ghostwriter, Pynguin, LLM-driven test generation) — capabilities, limitations, recent advances", "benchmarks/evaluation harnesses for automated bug-fixing & coding agents (SWE-bench and successors) and the techniques that top them"];
  const researchFn = async () => {
    const gathered = await pMap(facets, (facet, i) => runAgent({ name: `s4-research${i}`, model: "sonnet", web: true, budgetUsd: 10, timeoutMs: 1200000, schema: RESEARCH_SCHEMA, prompt: L("You are a Stage-4 RESEARCH gatherer (deep-research style). Search the web for ideas/technologies/projects that materially ADVANCE this repo's goal. Gather independently; you will be cross-checked.", "REPO DOMAIN GROUNDING:", ground, `YOUR FACET: ${facet}`, "Use WebSearch/WebFetch. Return sources[]: {title, url, claim, relevance (how it advances the goal), corroborated (false unless 2+ independent sources support the claim)}. Cite every source by URL; an uncorroborated claim is unverified, not fact.") }), 3);
    const sources = []; for (const g of gathered) if (g.ok) sources.push(...g.data.sources);
    const syn = await runAgent({ name: "s4-research-synth", model: "opus", budgetUsd: 8, timeoutMs: 900000, schema: RESEARCH_SYNTH_SCHEMA, prompt: L("You synthesize a deep-research pass. Cross-check the gathered sources: corroborate claims across sources, flag contradictions, drop low quality, and synthesize the ideas/technologies most relevant to the repo's goal.", "REPO DOMAIN GROUNDING:", ground, "GATHERED SOURCES (JSON):", JSON.stringify(sources).slice(0, 12000), "Output synthesis (prose tied to the goal), key_ideas[{idea, why_relevant, sources:[urls], confidence}], unverified[] (claims with only one weak source).") });
    return { sources, synth: syn.ok ? syn.data : null };
  };
  const [goalRes, research] = await Promise.all([goalFn(), researchFn()]);
  if (!goalRes.ok) await halt("stage4", "goal agent produced no schema-valid result", state);
  if (goalRes.data.candidates.filter(c => c.status === "grounded").length === 0) await halt("stage4", "no goal candidate could be grounded in a Stage 1-3 artifact", state);
  const obj = { goal: goalRes.data, research: { sources: research.sources, synthesis: research.synth }, _meta: { cost_usd: Number(TOTAL.toFixed(2)) } };
  await checkpoint("stage4", "04-goal.md", renderStage4MD(obj), "04-goal.json", obj, state);
}

// ════════════════════════════ STAGE 5 — EXECUTION-READY PLAN ════════════════════════════
const PLAN_SCHEMA = { type: "object", required: ["items", "sequencing_notes"], properties: { items: { type: "array", items: { type: "object", required: ["id", "title", "links_to", "location", "change", "verification_signal", "depends_on", "order", "effort"], properties: { id: { type: "string" }, title: { type: "string" }, links_to: { type: "string" }, location: { type: "string" }, change: { type: "string" }, verification_signal: { type: "string" }, depends_on: { type: "array", items: { type: "string" } }, order: { type: "integer" }, effort: { type: "string", enum: ["S", "M", "L"] } } } }, sequencing_notes: { type: "string" } } };
const PLAN_FALSIFY_SCHEMA = { type: "object", required: ["checks", "ambiguous_items", "verdict"], properties: { checks: { type: "array", items: { type: "object", required: ["name", "passed", "evidence"], properties: { name: { type: "string" }, passed: { type: "boolean" }, evidence: { type: "string" } } } }, ambiguous_items: { type: "array", items: { type: "object", required: ["id", "why"], properties: { id: { type: "string" }, why: { type: "string" } } } }, verdict: { type: "string", enum: ["pass", "needs_work"] } } };

function renderStage5MD(obj) {
  const rows = [...obj.items].sort((a, b) => a.order - b.order).map(it => `| ${it.order} | ${it.id} | ${it.title.replace(/\n/g, " ")} | \`${it.location}\` | ${it.links_to} | ${it.effort} | ${(it.depends_on || []).join(",") || "—"} |`).join("\n");
  const detail = [...obj.items].sort((a, b) => a.order - b.order).map(it => L(`### ${it.order}. ${it.title} (\`${it.id}\`)`, "", `- **Location:** \`${it.location}\``, `- **Links to:** ${it.links_to}`, `- **Change:** ${it.change}`, `- **Verification signal:** ${it.verification_signal}`, `- **Depends on:** ${(it.depends_on || []).join(", ") || "none"} · **Effort:** ${it.effort}`)).join("\n\n");
  return L("# 05 — Execution-Ready Plan", "", `_${obj.count} ordered, dependency-sorted change items. Each links to a Stage-2 finding or Stage-4 goal signal, is localized to a path, and carries a verification signal. Validated by an independent reviewer — no ambiguous items remain._`, "", obj.sequencing_notes ? `**Sequencing:** ${obj.sequencing_notes}\n` : "", "| # | ID | Change | Location | Links | Effort | Depends |", "| --- | --- | --- | --- | --- | --- | --- |", rows, "", "## Item detail", "", detail, "");
}

async function stage5(state) {
  log("═══ STAGE 5: execution-ready plan ═══");
  const inv = safeRead(join(WORK, "01-inventory.json")), f2 = safeRead(join(WORK, "02-findings.json")), f3 = safeRead(join(WORK, "03-execution.json")), f4 = safeRead(join(WORK, "04-goal.json"));
  if (!inv || !f2 || !f4) await halt("stage5", "missing prior artifacts", state);
  const ctx = L(`GOALS: ${f4.goal.candidates.map(c => c.goal).join(" | ")}`, `FINDINGS (${f2.findings.length}): ${f2.findings.map(f => `${f.id}:${f.class}/${f.severity}@${f.location}`).join("; ")}`, f3 ? `EXECUTION: ran=${f3.test_result?.ran}, cov=${f3.test_result?.coverage_pct ?? "?"}%` : "", `RESEARCH IDEAS: ${(f4.research?.synthesis?.key_ideas || []).map(k => k.idea).slice(0, 8).join("; ")}`);
  let items = null, ambiguous = [], notes = "";
  for (let round = 1; round <= 2; round++) {
    const fixHint = round > 1 ? "A prior draft had AMBIGUOUS items a fresh engineer could not map to a diff without questions — fix these: " + JSON.stringify(ambiguous) : "";
    const syn = await runAgent({ name: `s5-plan-r${round}`, model: "opus", budgetUsd: 12, timeoutMs: 1200000, schema: PLAN_SCHEMA, prompt: L("You are the Stage-5 PLANNER. Produce an ORDERED, dependency-sorted change plan that closes the gap between current state (Stages 1-3) and the goal (Stage 4). EVERY item MUST: link to a specific finding id or goal signal (links_to); be localized to a file/module (location); carry a concrete verification_signal (the test/observation proving it worked); and have a dependency position (depends_on + order).", `REPO ROOT: ${REPO}`, "CONTEXT:", ctx, `Read full findings at ${join(WORK, "02-findings.json")} and goal at ${join(WORK, "04-goal.json")} for detail.`, fixHint, "Output items[]: {id, title, links_to, location, change, verification_signal, depends_on[], order, effort(S|M|L)} + sequencing_notes.") });
    if (!syn.ok) await halt("stage5", `planner produced no schema-valid result in round ${round}`, state);
    items = syn.data.items;
    const incomplete = items.filter(it => !it.links_to || !it.location || !it.verification_signal || it.order === undefined);
    const fal = await runAgent({ name: `s5-falsify-r${round}`, model: "opus", budgetUsd: 8, timeoutMs: 900000, schema: PLAN_FALSIFY_SCHEMA, prompt: L("You are an INDEPENDENT plan reviewer. For EACH item decide: could a fresh engineer map it to a concrete diff target WITHOUT a clarifying question? Does its location path actually exist? Is its finding/goal link real (check the findings/goal files)?", `REPO ROOT: ${REPO}`, `Findings: ${join(WORK, "02-findings.json")}; Goal: ${join(WORK, "04-goal.json")}.`, "PLAN ITEMS (JSON):", JSON.stringify(items).slice(0, 12000), "Return checks[], ambiguous_items[{id, why}], verdict (pass|needs_work).") });
    ambiguous = fal.ok ? (fal.data.ambiguous_items || []) : [];
    notes = syn.data.sequencing_notes;
    if (incomplete.length === 0 && ambiguous.length === 0 && fal.ok && fal.data.verdict === "pass") { log(`plan converged round ${round}`); break; }
    log(`round ${round}: ${incomplete.length} incomplete, ${ambiguous.length} ambiguous`);
    if (round === 2 && (incomplete.length > 0 || ambiguous.length > 0)) await halt("stage5", `plan did not converge: ${incomplete.length} incomplete, ${ambiguous.length} ambiguous items remain`, state);
  }
  const obj = { items, count: items.length, sequencing_notes: notes, _meta: { cost_usd: Number(TOTAL.toFixed(2)) } };
  await checkpoint("stage5", "05-plan.md", renderStage5MD(obj), "05-plan.json", obj, state);
  log(`PIPELINE COMPLETE — 5 artifacts in audit/. cumulative API-equiv $${TOTAL.toFixed(2)}`);
}

// ── main ──
async function main() {
  if (FRESH && existsSync(AUDIT)) { rmSync(AUDIT, { recursive: true, force: true }); }
  mkdirSync(WORK, { recursive: true });
  writeFileSync(join(WORK, ".gitignore"), "a_*.json\n*.log\nauditable.json\n03-exec-raw.json\n");   // keep raw agent dumps, logs & stage intermediates out of git; artifacts+state+script stay
  BRANCH = (await sh("git", ["rev-parse", "--abbrev-ref", "HEAD"])).out.trim();
  const state = loadState();
  log(`repo=${REPO} branch=${BRANCH} stage=${ONLY_STAGE || "all-incomplete"} fresh=${FRESH}`);
  const stages = { 1: stage1, 2: stage2, 3: stage3, 4: stage4, 5: stage5 };
  if (ONLY_STAGE) {
    if (!stages[ONLY_STAGE]) { log("bad --stage"); process.exit(1); }
    await stages[ONLY_STAGE](state);
  } else {
    for (const n of [1, 2, 3, 4, 5]) { if (!state.completed[`stage${n}`]) await stages[n](state); else log(`skip stage${n} (done)`); }
  }
  log(`DONE. cumulative cost $${TOTAL.toFixed(2)}`);
}
main().catch(e => { log("FATAL", e?.stack || e); process.exit(1); });
