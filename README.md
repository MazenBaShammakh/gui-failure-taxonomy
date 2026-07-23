# GUI Agent Failure Taxonomy

A taxonomy of recurring GUI-agent failure modes (text-only / vision-only /
multimodal, across web / mobile / desktop), plus the real-world evidence
(tasks and runs) backing each one. This document is a practical "how do I
add X" guide. For the normative schema definition, see
`specs/taxonomy-structure.md`; for a fuller repository walkthrough, see
`specs/v2-repository-guide.md`.

## Repository layout

| Path | What it is |
|---|---|
| `taxonomy/v2/mobile.yaml`, `web.yaml`, `cross-platform.yaml`, `desktop.yaml` | The **failure type spine** — Category → Failure, one entry per failure concept. No embedded evidence. Split **by platform**. |
| `taxonomy/v3/F-PRC.yaml`, `F-IDT.yaml`, … (one per category code) | The same spine for the v3 corpus, split **by category** instead — see "Which file does a type go in?" below. |
| `taxonomy/<folder>/runs.yaml` | The **evidence**: every real-world Task attempted, each holding one or more Runs, each Run tagging 1+ failure types. |
| `taxonomy/v2/overview.md` | Generated summary (tables + mermaid diagrams). **Do not hand-edit** — see "After editing" below. |
| `specs/taxonomy-structure.md` | Normative record shapes, ID scheme, facets. |
| `specs/v2-repository-guide.md` | Broader thesis-facing repo walkthrough. |
| `app.py` | Streamlit browser for the taxonomy (`streamlit run app.py`). |
| `helper/` | Scripts: verification, `overview.md` generation, and the one-off Task/Run migration tooling. |
| `benchmark/*.jsonl` | External task corpus (Mind2Web, AITW, LlamaTouch, OSWorld, and the team's own `gui-failure-suite`). |

## Setup

```
pip install -r requirements.txt
streamlit run app.py
```

The browser has an "Auto-refresh" sidebar option if you're editing yaml
files while it's open — Streamlit's dev-mode file watcher only tracks `.py`
files, so it won't otherwise notice yaml edits without a manual tab refresh.

## The model, in short

- A **failure type** (`F-{CATEGORY}-{NNN}`, e.g. `F-INS-01`) names a
  concept — "blocking modal with no close affordance" — platform- and
  representation-agnostic. It carries a description, remediation, and
  *predicted* (`expected`) facet coverage.
- A **Task** (`T-{NNN}`) is one real-world `(app, task)` attempt.
- A **Run** (`{task_id}-{letter}`, e.g. `T-014-a`) is one concrete
  execution against a Task: one representation, one platform, one outcome.
- A Run tags **one or more** failure types via `failures[]` — this is a
  many-to-many link, and each tag carries its own `cause`/`stage` (they can
  differ per type the same run exhibits — see the LinkedIn example in
  `specs/taxonomy-structure.md` §6).

A type's `observed` facet values (which platforms/representations it's
actually been seen on) are **never stored** — they're derived from whichever
runs tag that type, everywhere they're read (`app.py`, the helper scripts).
Don't add an `observed:` key to a type; there's nothing to keep in sync.

## Adding a new failure type

### Which file does a type go in?

**v3 — by category.** The file is fully determined by the type's category:
`perceptibility` → `F-PRC.yaml`, `state_feedback` → `F-FBK.yaml`, and so on
(code table below). Platform is a *facet* (`facets.platform`), not a file,
so a type applying to two platforms still lives in exactly one file and
never has to move as evidence accumulates. `app.py` warns on load if an
entry's `category` field disagrees with the file it sits in.

**v2 — by platform** (kept as-is; don't restructure it):
   - Observed on exactly one platform so far → that platform's file
     (`mobile.yaml` / `web.yaml` / `desktop.yaml`).
   - Genuinely observed on 2+ platforms already → `cross-platform.yaml`.
   - Not observed at all yet (a predicted candidate) → whichever platform
     file it's predicted for; `desktop.yaml`'s types are all like this today.

   If a type observed on one platform later gains evidence on a second, move
   its whole block into `cross-platform.yaml` (see that file's header for
   the exact rule) — don't leave it split.

### Steps

1. **Pick the file** per the rule above.

2. **Pick an ID.** `F-{CATEGORY}-{NNN}`, where `{CATEGORY}` is the 3-letter
   code (table below) and `{NNN}` is the next free number **for that
   category**. In v3 that whole category lives in one file, so it's just:
   ```
   grep "id: F-<CATEGORY>-" taxonomy/v3/F-<CATEGORY>.yaml
   ```
   In v2 the category is spread across all four platform files, so you must
   check all of them — a duplicate type ID has been a real bug before (see
   `specs/taxonomy-structure.md` §7):
   ```
   grep -h "id: F-<CATEGORY>-" taxonomy/v2/*.yaml
   ```

3. **Write the record:**
   ```yaml
   - id: F-INS-04
     category: interaction_scope
     failure: Short Human-Readable Name
     description: >
       What the failure is and why it happens.
     assessment_ref: candidate   # or an Fx.y ref into failure-assessment.md
     facets:
       representation:
         expected: [vision-only, multimodal]   # predicted; no `observed` key
       platform:
         expected: [web]
       cause: software-side      # dominant/characteristic case: software-side | agent-side | joint
       stage: prediction         # dominant/characteristic case: prediction | execution | unclear
     remediation:
       fix: >
         The proposed software-/design-side change.
       helps: [vision-only, multimodal]
   ```

4. If it's purely predicted (no evidence yet), stop here — no Task/Run
   needed. Add evidence later the same way you'd add it to any type (below).

## Adding a new observation (Task + Run)

1. **Check if the Task already exists.** Search `runs.yaml` for the same
   `(app, task)` pair. If it does, you're adding a **Run** to it (a new
   representation attempt at the same real-world task); if not, create a
   **new Task**.

2. **New Task** — next free `T-{NNN}` (sequential, not per-category):
   ```yaml
   - id: T-050
     task_id: null   # see "task_id" below
     app: Some App
     task: The task instruction text.
     source: live                   # controlled | live | benchmark | literature
     runs:
       - id: T-050-a
         run_id: 2026-06-29_130330  # harness run id — see below (v3 onward)
         representation: multimodal
         platform: web
         outcome: failed             # succeeded | failed
         notes: >
           What actually happened — evidence, trace pointer, screenshot ref.
         failures:
           - type: F-INS-04
             cause: software-side
             stage: prediction
   ```

3. **Adding a Run to an existing Task** — append to that Task's `runs:`
   list with the next unused letter (`T-050-b`, `T-050-c`, ...). Common case:
   the RQ1 contrast — the same task run under a different representation,
   e.g. vision-only fails / multimodal succeeds on the same screen.

4. **`source`** — on the **Task**, not the Run (v3 onward; v2 has it on each
   Run). It describes the application targeted, which can't differ between
   runs of one task. Derive it, don't pick it:
   - `app` contains `localhost` or `com.mazenbashammakh` → `controlled`
     (our instrumented build, whether or not a fault was injected).
   - else `task_id` starts with `gui-failure-suite` → `live` (a real site).
   - else → `benchmark` (the benchmark app as shipped).

   `literature` still applies to a Task with no execution behind it.

5. **`run_id`** — the id the agent harness gave the execution,
   `YYYY-MM-DD_HHMMSS` (e.g. `2026-06-29_130330`), copied verbatim from the
   run-result JSON. It's what gets you from a row here back to the raw trace;
   `id` (`T-050-a`) stays this repo's own short handle. Set it on every v3
   run that came from a real execution — `source: literature` runs have none.
   v2 predates the field and doesn't have it anywhere.

   **Don't quote it, and don't reformat it.** `2026-06-29_130330` loads as a
   string precisely because of the `_`; write it `2026-06-29T13:03:30` or
   `2026-06-29 13:03:30` and YAML hands back a `datetime` object instead,
   which no longer matches the harness's id.

6. **`task_id`** — set it only if this task corresponds to a record in
   `benchmark/*.jsonl`:
   - `source: benchmark` runs: set it to that record's id (e.g.
     `mind2web-web-0987`, `aitw-mobile-0068`).
   - `source: live`/`controlled` runs: leave it `null` **unless** the task
     was actually run against a `gui-failure-suite-*` entry in
     `benchmark/*.jsonl` (the planned task set for future controlled/live
     runs) — if so, use that id.

7. **One run, multiple failure types?** Only tag a single run with more
   than one type in `failures[]` when it's genuinely **the same execution**
   exhibiting more than one distinct mechanism — evidenced by e.g. an
   identical source citation/screenshot for both angles. If two attempts
   merely share a task (different representations, or different documented
   examples/sessions), they're **separate Runs**, each with one tag —
   different representation always means a different execution. See
   `specs/taxonomy-structure.md` §3.3 for the full rule and a worked
   example.

6. `cause`/`stage` go on each `failures[]` entry, not the run — if a run
   tags two types, each tag gets its own `cause`/`stage` (they can
   legitimately differ, e.g. `prediction` for one mechanism and `execution`
   for another on the very same run).

## After editing

1. **Regenerate `overview.md`** — never hand-edit it:
   ```
   python helper/generate_overview.py
   ```
2. **Verify against the benchmark corpus** if you touched anything
   `source: benchmark`-related, or just to sanity-check the whole file:
   ```
   python helper/verify_benchmark_observations.py
   ```
   Read-only; writes `helper/benchmark_verification_report.md`. Flags
   resolution failures, field mismatches, and (new) `task_id` drift.
3. **Quick parse/count sanity check:**
   ```
   python -c "import yaml; from pathlib import Path
   for f in ['mobile','web','cross-platform','desktop']:
       print(f, len(yaml.safe_load(open(f'taxonomy/v2/{f}.yaml', encoding='utf-8'))))
   runs = yaml.safe_load(open('taxonomy/v2/runs.yaml', encoding='utf-8'))
   print('tasks', len(runs), 'runs', sum(len(t['runs']) for t in runs))"
   ```
4. **Look at it** — `streamlit run app.py`, expand the type(s) you touched.
   The browser groups evidence by **observation** (one card per Task, with
   its Run(s) nested inside — two runs of the same task are one
   observation, not two); confirm the new run renders in the right
   observation card, and (if it tags more than one type) that the "Same run
   also evidences" cross-link shows up on both types' panels.

## Category codes

| Code | Category |
|---|---|
| `PRC` | Perceptibility |
| `IDT` | Identifiability |
| `STR` | Structural Consistency |
| `INA` | Interaction Affordance |
| `NAV` | Navigation Discoverability |
| `CNT` | Content Organization |
| `FBK` | State Feedback |
| `TMP` | Temporal Dynamics |
| `INS` | Interaction Scope |

## Common mistakes

- **Adding a duplicate type ID.** In v2, always `grep` all four type files
  for the category code before picking a number — per-file numbering has
  caused a real collision before. (v3's category-per-file split removes this
  failure mode: one category, one file.)
- **Filing a v3 type by platform.** `F-PRC.yaml` etc. are category files —
  a web-only perceptibility failure still goes in `F-PRC.yaml`, with `web`
  in `facets.platform.expected`. The app flags category/file mismatches.
- **Adding an `observed:` key to a type's facets.** It's derived, not
  stored — don't add it, it'll just be ignored (or worse, drift from
  reality and mislead a reader).
- **Merging two different-representation runs into one.** A run is one
  execution under one representation; different representation always means
  a different run, even on the identical task/screen.
- **Hand-editing `overview.md`.** It's generated — your edits will be
  overwritten the next time someone runs `helper/generate_overview.py`
  (which should be every time `taxonomy/v2/*.yaml` changes).
