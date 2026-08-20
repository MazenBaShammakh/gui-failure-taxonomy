# GUI Failure Taxonomy

A taxonomy of recurring GUI-agent failure modes — organized by **category**,
**cause**, and **action stage** — backed by real evidence (tasks and runs) from
benchmark and controlled-lab executions, plus a browser app for exploring it.

---

## Overview

When a GUI agent (text-only, vision-only, or multimodal) fails a task, the
failure usually isn't random — it recurs across apps, platforms, and agents in
a small number of recognizable shapes. This repo catalogs those shapes as
**failure types**, and logs the concrete evidence for each one:

- A **failure type** (e.g. "blocking modal with no close affordance") names a
  recurring failure concept — platform- and agent-agnostic — with a
  description and a proposed remediation.
- A **Task** is one real-world `(app, task instruction)` pair that was
  actually attempted.
- A **Run** is one concrete execution of a Task — one representation
  (text-only / vision-only / multimodal), one platform, one outcome
  (`succeeded` / `failed`) — tagging one or more failure types with the
  `cause` (software-side, agent-side, or joint) and `stage` (prediction or
  execution) that applied for that run.

A Task can have multiple Runs (e.g. the same screen attempted text-only and
multimodally, to see whether richer perception changes the outcome).

---

## The taxonomy, in brief

**29 failure types across 9 categories**, evidenced by **55 tasks and 177
runs** so far:

| Code | Category | Question it answers | Types |
| ---- | --------------------------- | ------------------------------------------------- | ----: |
| PRC  | Perceptibility              | Can the agent see the element exists?              |     6 |
| IDT  | Identifiability              | Can the agent understand what the element is?      |     5 |
| INA  | Interaction Affordance         | Can the agent figure out how to interact?          |     1 |
| INS  | Interaction Scope                      | Are actions contained to the intended target?      |     4 |
| NAV  | Navigation Discoverability      | Can the agent find the path to the target?         |     2 |
| CNT  | Content Organization             | Is information structured for agent reasoning?     |     3 |
| STR  | Structural Consistency        | Does the structured tree match the rendered UI?    |     2 |
| FBK  | State Feedback                     | Does the UI communicate state and outcomes?        |     2 |
| TMP  | Temporal Dynamics                    | Can the agent keep up with UI changes over time?   |     4 |

Across the 177 logged runs: failures are overwhelmingly **software-side**
(162 of 176 tagged causes), and mostly occur at the **prediction** stage —
the agent reasoning incorrectly before acting (136) — rather than at
**execution** (40), where the agent reasoned correctly but the action itself
misfired. Evidence spans mobile (120 runs), desktop (38), and web (19), drawn
from both benchmark corpora (Mind2Web, AITW, LlamaTouch, OSWorld) and a
controlled, fault-injectable lab app.

A few representative examples from the catalog:

- **Perceptibility** — elements that are visually present but missing from
  the DOM/accessibility tree entirely, so the agent has nothing to target
  (observed on CarMax, Ticketmaster, Megabus listings).
- **Identifiability** — a single icon overloaded with two purposes (e.g. a
  combined search-and-navigation icon), causing the agent to trigger the
  wrong action; or a decorative element styled to look interactive when it
  isn't.
- **Interaction Affordance** — gesture-only controls (swipe-to-delete,
  long-press) with no visual cue, which vision-only agents cannot discover
  from a screenshot alone; multimodal agents only succeed when the gesture is
  also declared in the accessibility tree.
- **Navigation Discoverability** — critical links buried in hover-only
  dropdown menus, invisible to any agent that can't hover.
- **Temporal Dynamics** — content injected into the page *after* the agent's
  DOM/visual snapshot was captured, so the agent acts on stale state (e.g. a
  popup that appears just after the screenshot).
- **Interaction Scope** — a modal that intercepts the whole page with no
  usable close affordance, so the agent either stalls or acts blindly around
  it.

---

## Prerequisites & Setup

Python 3.10+ and pip.

```bash
git clone <repo-url>
cd gui-failure-taxonomy
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

This installs `pyyaml` (reads the taxonomy YAML) and `streamlit` (the browser
app) — there's no separate build step needed to run it.

---

## Running the visualizer

```bash
streamlit run app.py
```

This starts a local server (by default at `http://localhost:8501`) and opens
it in your browser. From there you can:

- Filter the catalog by category, cause, stage, representation, platform,
  evidence source, and outcome, or free-text search, from the sidebar.
- Expand a category to see its failure types; expand a type to see its
  description, remediation, and every Task/Run logged against it.
- Turn on **Auto-refresh** in the sidebar if you're hand-editing the taxonomy
  YAML files while the app is open — Streamlit's file watcher only reloads on
  `.py` changes by default, not YAML edits.

To stop the app, go back to the terminal and press `Ctrl+C`.

---

## Repository layout

| Path                      | What it is                                                                 |
| -------------------------- | --------------------------------------------------------------------------- |
| `taxonomy/*.yaml` (except `runs.yaml`) | The failure type definitions — one file per category (e.g. `PRC.yaml`). |
| `taxonomy/runs.yaml`      | The evidence log — every Task attempted, each with one or more Runs.          |
| `app.py`                      | The Streamlit browser (`streamlit run app.py`).                               |
| `benchmark/*.jsonl`               | The external task corpus (Mind2Web, AITW, LlamaTouch, OSWorld, gui-failure-suite) that benchmark-sourced Tasks are drawn from. |

---

## Extending the taxonomy

### Adding a new failure type

1. **Pick the file.** Determined by category: `perceptibility` → `PRC.yaml`,
   `state_feedback` → `FBK.yaml`, and so on (see the category table above
   for all 9 codes). A type gets exactly one file regardless of how many
   platforms it applies to — platform is a *facet*, not a file.
2. **Pick an ID.** `{CATEGORY}-{NNN}`, the next free number for that
   category:
   ```bash
   grep "id: <CATEGORY>-" taxonomy/<CATEGORY>.yaml
   ```
3. **Write the record:**
   ```yaml
   - id: INS-04
     category: interaction_scope
     failure: Short Human-Readable Name
     description: >
       What the failure is and why it happens.
     facets:
       representation:
         expected: [vision-only, multimodal]
       platform:
         expected: [web]
       cause: software-side      # software-side | agent-side | joint
       stage: prediction         # prediction | execution | unclear
     remediation:
       fix: >
         The proposed software-/design-side change.
       helps: [vision-only, multimodal]
   ```
4. If it's purely predicted (no evidence yet), stop here — evidence can be
   added later the same way as below.

### Adding a new observation (Task + Run)

1. **Check if the Task already exists** — search `runs.yaml` for the same
   `(app, task)` pair. If it does, you're adding a **Run** to it; if not,
   create a **new Task**.
2. **New Task** — next free `T-{NNN}`:
   ```yaml
   - id: T-050
     app: Some App
     task: The task instruction text.
     source: live                   # controlled | live | benchmark | literature
     runs:
       - id: T-050-a
         run_id: 2026-06-29_130330  # the harness's own run id, verbatim
         representation: multimodal
         platform: web
         outcome: failed             # succeeded | failed
         notes: >
           What actually happened — evidence, trace pointer, screenshot ref.
         failures:
           - type: INS-04
             cause: software-side
             stage: prediction
   ```
3. **Adding a Run to an existing Task** — append to that Task's `runs:` with
   the next unused letter (`T-050-b`, `T-050-c`, ...).

---

## Relationship to the other repos

This taxonomy is one of four repos in a research suite studying GUI-agent
failure behavior: `gui-failure-suite` provides the task corpus, `gui-failure-lab`
hosts controlled apps with injectable defects, `gui-failure-runner` executes
agents against tasks and produces run results, and this repo classifies the
resulting failures and stores the evidence trail — a run's `run_id` here is
the same id the runner assigned to that execution.
