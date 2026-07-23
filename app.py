#!/usr/bin/env python3
"""Streamlit browser for the GUI Agent Failure Taxonomy.

Data model (see specs/taxonomy-structure.md): failure Types are the spine,
defined in every *.yaml of taxonomy/<folder>/ except runs.yaml. How those
files are split is a per-folder convention the loader doesn't care about:
v2 splits by platform ({mobile,web,cross-platform,desktop}.yaml), v3 splits
by category (F-PRC.yaml, F-IDT.yaml, … one per category code). Real-world
evidence lives separately in taxonomy/<folder>/runs.yaml as Tasks, each
holding one or more Runs, and each Run tags 1+ Types via a `failures[]`
list (a many-to-many Run<->Type link). A type's `observed` facet values are
not stored -- they're derived here from whichever runs tag that type.

`<folder>` defaults to `v3` but is switchable from the sidebar -- any
subdirectory of taxonomy/ containing a runs.yaml is auto-detected.

Evidence is rendered as plain indented text: a bold task line followed by
indented "↳" run lines, separated by a thin divider. This began as
`ui_prototypes/option_c_flat_list.py` and was promoted to the main app; the
previous nested-card layout is kept for reference at
`ui_prototypes/option_original_cards.py`.

Run: streamlit run app.py
"""

from collections import defaultdict
from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent
TAXONOMY_ROOT = ROOT / "taxonomy"
DEFAULT_TAXONOMY_FOLDER = "v3"

CATEGORY_LABELS = {
    "perceptibility": "Perceptibility",
    "identifiability": "Identifiability",
    "structural_consistency": "Structural Consistency",
    "interaction_affordance": "Interaction Affordance",
    "navigation_discoverability": "Navigation Discoverability",
    "content_organization": "Content Organization",
    "state_feedback": "State Feedback",
    "temporal_dynamics": "Temporal Dynamics",
    "interaction_scope": "Interaction Scope",
}

CAUSE_BADGE = {
    "software-side": ":orange[software-side]",
    "agent-side": ":blue[agent-side]",
    "joint": ":violet[joint]",
}

STAGE_BADGE = {
    "prediction": ":yellow[prediction]",
    "execution": ":green[execution]",
    "unclear": ":gray[unclear]",
}

SOURCE_BADGE = {
    "controlled": ":blue[controlled]",
    "live": ":green[live]",
    "benchmark": ":orange[benchmark]",
    "literature": ":gray[literature]",
}

OUTCOME_BADGE = {
    "succeeded": ":green[✓ succeeded]",
    "failed": ":red[✗ failed]",
}

REPRESENTATIONS = ["text-only", "vision-only", "multimodal"]
PLATFORMS = ["web", "mobile", "desktop"]

CATEGORY_CODES = {
    "perceptibility": "PRC",
    "identifiability": "IDT",
    "structural_consistency": "STR",
    "interaction_affordance": "INA",
    "navigation_discoverability": "NAV",
    "content_organization": "CNT",
    "state_feedback": "FBK",
    "temporal_dynamics": "TMP",
    "interaction_scope": "INS",
}

# v3 convention: one file per category, named for that category's code.
# Empty for a v2-style folder, where file stems are platforms instead.
CODE_TO_CATEGORY = {f"F-{code}": cat for cat, code in CATEGORY_CODES.items()}

RUNS_FILE = "runs.yaml"


def discover_taxonomy_folders() -> list[str]:
    if not TAXONOMY_ROOT.is_dir():
        return [DEFAULT_TAXONOMY_FOLDER]
    folders = sorted(
        p.name for p in TAXONOMY_ROOT.iterdir()
        if p.is_dir() and (p / RUNS_FILE).exists()
    )
    return folders or [DEFAULT_TAXONOMY_FOLDER]


def _yaml_fingerprint(taxonomy_dir: Path) -> tuple[tuple[str, int], ...]:
    return tuple(
        (path.name, path.stat().st_mtime_ns)
        for path in sorted(taxonomy_dir.glob("*.yaml"))
    )


@st.cache_data
def load_types(taxonomy_dir: Path, fingerprint: tuple[tuple[str, int], ...]) -> list[dict]:
    types = []
    for path in sorted(taxonomy_dir.glob("*.yaml")):
        if path.name == RUNS_FILE:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not data:
            continue
        for t in data:
            t = dict(t)
            t["_source_file"] = path.stem
            types.append(t)
    return types


@st.cache_data
def load_tasks(taxonomy_dir: Path, fingerprint: tuple[tuple[str, int], ...]) -> list[dict]:
    path = taxonomy_dir / RUNS_FILE
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def category_filename_mismatches(types: list[dict]) -> list[str]:
    """Types sitting in a category-named file (v3) whose `category` field
    disagrees with the filename -- e.g. an entry pasted into F-PRC.yaml but
    left as `category: state_feedback`. `category` is kept in every entry so
    records stay self-contained, which means it can drift; this catches that.
    Returns [] for a v2-style folder, where filenames carry no category."""
    problems = []
    for t in types:
        expected = CODE_TO_CATEGORY.get(t["_source_file"])
        if expected and t.get("category") != expected:
            problems.append(
                f"`{t.get('id', '?')}` in `{t['_source_file']}.yaml` has "
                f"`category: {t.get('category')}`, expected `{expected}`"
            )
    return problems


def source_of(task: dict, run: dict) -> str | None:
    """`source` describes the application an attempt targeted, so it belongs
    to the Task -- it cannot differ between runs of the same task. v3 stores
    it there. v2 stored it on each Run, so fall back to that; both folders
    have to keep working."""
    return task.get("source") or run.get("source")


def build_type_index(tasks: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = defaultdict(list)
    for task in tasks:
        for run in task.get("runs", []) or []:
            for edge in run.get("failures", []) or []:
                index[edge["type"]].append(
                    {"task": task, "run": run, "edge": edge})
    return index


def facet_values(t: dict, index: dict[str, list[dict]], facet: str) -> tuple[list[str], list[str]]:
    entries = index.get(t["id"], [])
    observed = sorted({e["run"].get(facet)
                      for e in entries if e["run"].get(facet)})
    expected = list((t.get("facets", {}).get(
        facet, {}) or {}).get("expected") or [])
    return observed, expected


def facet_chips(observed: list[str], expected: list[str]) -> str:
    chips = [f"`{v}`" for v in observed] + \
        [f"⬜ `{v}`" for v in expected if v not in observed]
    return " ".join(chips) if chips else "—"


def observation_count(t: dict, index: dict[str, list[dict]]) -> int:
    return len({e["task"]["id"] for e in index.get(t["id"], [])})


def render_evidence_flat(t: dict, index: dict[str, list[dict]], type_labels: dict[str, str]) -> None:
    """Evidence as plain indented lines: no bordered containers, a thin
    `---` divider between observations instead of a box."""
    entries = index.get(t["id"], [])
    if not entries:
        st.info("No logged runs — predicted / expected only.")
        return

    by_task: dict[str, dict] = {}
    for e in entries:
        task_id = e["task"]["id"]
        by_task.setdefault(task_id, {"task": e["task"], "items": []})[
            "items"].append(e)

    st.markdown(f"**Observations ({len(by_task)})**")
    for i, group in enumerate(by_task.values()):
        task = group["task"]
        header = f"**`{task['id']}`** · {task.get('app', '—')}"
        if task.get("task"):
            header += f" · *{task['task']}*"
        st.markdown(header)
        caption_bits = []
        if task.get("task_id"):
            caption_bits.append(f"Task ID: `{task['task_id']}`")
        if task.get("source"):
            # v3: source lives on the Task, so show it once here rather
            # than repeating it on every run line below.
            caption_bits.append(
                f"Source: {SOURCE_BADGE.get(task['source'], task['source'])}")
        if caption_bits:
            st.caption("  ·  ".join(caption_bits))

        for e in group["items"]:
            run, edge = e["run"], e["edge"]
            other = [f for f in run.get(
                "failures", []) if f["type"] != t["id"]]
            other_txt = ""
            if other:
                others = ", ".join(
                    f"`{f['type']}` ({type_labels.get(f['type'], f['type'])})" for f in other)
                other_txt = f"  ·  also evidences: {others}"
            unverified = "  :gray[(unverified)]" if run.get(
                "verified") is False else ""
            # run_id is the harness's own id for the execution (v3 onward,
            # absent in v2) -- the pointer back to the raw trace. Rendered
            # as-is on purpose: one written with a `T`/space separator
            # instead of `_` parses as a datetime, and showing YAML's
            # reformatting of it is the tell that it's wrong.
            harness_id = run.get("run_id")
            harness_txt = f"  :gray[{harness_id}]" if harness_id else ""
            # Only repeat source per run when the Task doesn't carry it (v2).
            run_source = None if task.get("source") else run.get("source")
            source_txt = (
                f"  ·  {SOURCE_BADGE.get(run_source, run_source)}"
                if run_source else "")
            st.markdown(
                f"&nbsp;&nbsp;&nbsp;&nbsp;↳ `{run['id']}`{harness_txt}{unverified}  ·  "
                f"{run.get('representation', '—')} · {run.get('platform', '—')}  ·  "
                f"{OUTCOME_BADGE.get(run.get('outcome'), run.get('outcome', '—'))}"
                f"{source_txt}{other_txt}"
            )
            if run.get("notes"):
                st.caption(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{run['notes'].strip()}")
            edge_cause, edge_stage = edge.get("cause"), edge.get("stage")
            type_cause = (t.get("facets", {}) or {}).get("cause")
            type_stage = (t.get("facets", {}) or {}).get("stage")
            if (edge_cause, edge_stage) != (type_cause, type_stage):
                st.caption(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This run: "
                    f"{CAUSE_BADGE.get(edge_cause, edge_cause or '—')} · "
                    f"{STAGE_BADGE.get(edge_stage, edge_stage or '—')}"
                )
        if i < len(by_task) - 1:
            st.markdown("---")


def render_type(t: dict, index: dict[str, list[dict]], type_labels: dict[str, str]) -> None:
    category_label = CATEGORY_LABELS.get(t["category"], t["category"])
    remediation = t.get("remediation", {}) or {}

    left, right = st.columns([3, 1])

    with left:
        st.markdown(f"#### {t['failure'].replace('_', ' ')}")
        st.write(t.get("description", "").strip())
        if remediation.get("fix"):
            st.markdown("**Remediation (RQ4)**")
            st.write(remediation["fix"].strip())
            helps = remediation.get("helps") or []
            if helps:
                st.caption("Helps: " + ", ".join(f"`{h}`" for h in helps))

    facets = t.get("facets", {}) or {}
    cause = facets.get("cause")
    stage = facets.get("stage")

    with right:
        st.markdown("**Attributes**")
        st.markdown(f"File: `{t['_source_file']}`")
        st.markdown(f"Category: `{category_label}`")
        st.markdown(
            f"Cause: {CAUSE_BADGE.get(cause, cause or '—')}")
        st.markdown(
            f"Stage: {STAGE_BADGE.get(stage, stage or '—')}")
        if t.get("assessment_ref"):
            st.markdown(f"Assessment ref: `{t['assessment_ref']}`")

        rep_obs, rep_exp = facet_values(t, index, "representation")
        plat_obs, plat_exp = facet_values(t, index, "platform")
        st.markdown("**Representation**")
        st.markdown(facet_chips(rep_obs, rep_exp))
        st.markdown("**Platform**")
        st.markdown(facet_chips(plat_obs, plat_exp))

    render_evidence_flat(t, index, type_labels)


def main() -> None:
    st.set_page_config(page_title="GUI Failure Taxonomy",
                       page_icon="🧭", layout="wide")

    available_folders = discover_taxonomy_folders()
    with st.sidebar:
        qp_folder = st.query_params.get("folder")
        if qp_folder in available_folders:
            default_folder = qp_folder
        elif DEFAULT_TAXONOMY_FOLDER in available_folders:
            default_folder = DEFAULT_TAXONOMY_FOLDER
        else:
            default_folder = available_folders[0]
        selected_folder = st.selectbox(
            "Taxonomy folder", available_folders,
            index=available_folders.index(default_folder),
        )
        if selected_folder != DEFAULT_TAXONOMY_FOLDER:
            st.query_params["folder"] = selected_folder
        elif "folder" in st.query_params:
            st.query_params.pop("folder", None)
        st.divider()

    taxonomy_dir = TAXONOMY_ROOT / selected_folder

    st.title("GUI Failure Taxonomy")
    st.caption(
        f"Browse the taxonomy in `taxonomy/{selected_folder}/`. Types "
        "(Category → Failure) are the spine; real-world evidence is a Task "
        "with one or more Runs in `runs.yaml`, and each Run tags one or "
        "more Types."
    )

    fingerprint = _yaml_fingerprint(taxonomy_dir)
    types = load_types(taxonomy_dir, fingerprint)
    tasks = load_tasks(taxonomy_dir, fingerprint)
    index = build_type_index(tasks)
    type_labels = {t["id"]: t["failure"] for t in types}

    mismatches = category_filename_mismatches(types)
    if mismatches:
        st.warning("Category/file mismatch:\n\n" +
                   "\n".join(f"- {m}" for m in mismatches))

    with st.sidebar:
        st.header("Filters")

        present_cats = {t["category"] for t in types if t.get("category")}
        all_cats = [c for c in CATEGORY_LABELS if c in present_cats]
        all_cats += sorted(present_cats - set(all_cats))
        all_causes = sorted({t.get("facets", {}).get("cause")
                             for t in types if t.get("facets", {}).get("cause")})
        all_stages = sorted({t.get("facets", {}).get("stage")
                             for t in types if t.get("facets", {}).get("stage")})
        all_sources = sorted({s for task in tasks
                              for run in task.get("runs", []) or []
                              if (s := source_of(task, run))})
        all_outcomes = sorted({run.get("outcome") for task in tasks
                               for run in task.get("runs", []) if run.get("outcome")})

        sel_cats = st.multiselect(
            "Category", all_cats, default=all_cats,
            format_func=lambda c: CATEGORY_LABELS.get(c, c))
        sel_causes = st.multiselect("Cause", all_causes, default=all_causes)
        sel_stages = st.multiselect("Stage", all_stages, default=all_stages)

        st.divider()
        sel_reps = st.multiselect(
            "Representation", REPRESENTATIONS, default=REPRESENTATIONS)
        sel_plats = st.multiselect("Platform", PLATFORMS, default=PLATFORMS)
        observed_only = st.checkbox(
            "Observed only (exclude expected-only matches)", value=False,
        )

        st.divider()
        sel_sources = st.multiselect(
            "Run source", all_sources, default=all_sources)
        sel_outcomes = st.multiselect(
            "Run outcome", all_outcomes, default=all_outcomes)

        st.divider()
        search = st.text_input(
            "Search", placeholder="failure name, description, or ID…")

        st.divider()
        try:
            qp_interval = int(st.query_params.get("interval", "10"))
        except (TypeError, ValueError):
            qp_interval = 10
        qp_interval = min(max(qp_interval, 3), 300)

        auto_refresh = st.checkbox(
            "Auto-refresh", value=st.query_params.get("autorefresh") == "1",
        )
        if auto_refresh:
            refresh_secs = int(st.number_input(
                "Every N seconds", min_value=3, max_value=300, value=qp_interval, step=1,
            ))
            st.query_params["autorefresh"] = "1"
            st.query_params["interval"] = str(refresh_secs)
            st.markdown(
                f'<meta http-equiv="refresh" content="{refresh_secs}">',
                unsafe_allow_html=True,
            )
        elif "autorefresh" in st.query_params or "interval" in st.query_params:
            st.query_params.pop("autorefresh", None)
            st.query_params.pop("interval", None)

    def type_matches(t: dict) -> bool:
        if t.get("category") not in sel_cats:
            return False
        cause = t.get("facets", {}).get("cause")
        if cause not in sel_causes:
            return False
        stage = t.get("facets", {}).get("stage")
        if stage not in sel_stages:
            return False

        rep_obs, rep_exp = facet_values(t, index, "representation")
        rep_pool = rep_obs if observed_only else set(rep_obs) | set(rep_exp)
        if not (set(rep_pool) & set(sel_reps)):
            return False

        plat_obs, plat_exp = facet_values(t, index, "platform")
        plat_pool = plat_obs if observed_only else set(
            plat_obs) | set(plat_exp)
        if not (set(plat_pool) & set(sel_plats)):
            return False

        entries = index.get(t["id"], [])
        if entries:
            if not any(source_of(e["task"], e["run"]) in sel_sources for e in entries):
                return False
            if not any(e["run"].get("outcome") in sel_outcomes for e in entries):
                return False

        q = search.strip().lower()
        if q:
            haystack = " ".join(
                [t.get("id", ""), t.get("failure", ""),
                 t.get("description", "")]
            ).lower()
            if q not in haystack:
                return False

        return True

    filtered = [t for t in types if type_matches(t)]
    filtered.sort(key=lambda t: (t["_source_file"], t["id"]))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Types", len(filtered))
    m2.metric("Observations", sum(observation_count(t, index)
              for t in filtered))
    m3.metric("With observations", sum(
        1 for t in filtered if index.get(t["id"])))
    m4.metric("Categories", len({t["category"] for t in filtered}))

    st.divider()

    if not filtered:
        st.info("No types match the current filters.")
        return

    present_categories = {t["category"] for t in filtered}
    ordered_categories = [
        c for c in CATEGORY_LABELS if c in present_categories]
    ordered_categories += sorted(present_categories - set(ordered_categories))

    for category in ordered_categories:
        group = [t for t in filtered if t["category"] == category]
        group.sort(key=lambda t: (t["id"], t["_source_file"]))

        category_label = CATEGORY_LABELS.get(category, category)
        n_types = len(group)
        n_obs = sum(observation_count(t, index) for t in group)

        # No redundant metric row here (unlike app.py) -- the heading below
        # already states types/observations counts in text.
        st.markdown(
            f"## {category_label}  ·  {n_types} types  ·  "
            f"{n_obs} observation{'s' if n_obs != 1 else ''}")
        st.divider()

        for t in group:
            n_obs_t = observation_count(t, index)
            badge = f"({n_obs_t} observation{'s' if n_obs_t != 1 else ''})" if n_obs_t else "(predicted only)"
            # Category files repeat the section header; only show the source
            # file when it adds something (v2: the type's platform).
            origin = ("" if t["_source_file"] in CODE_TO_CATEGORY
                      else f"{t['_source_file']}  ")
            label = f"{t['id']}  ·  {t['failure'].replace('_', ' ')}  ·  {origin}{badge}"
            with st.expander(label, expanded=False):
                render_type(t, index, type_labels)

        st.divider()


if __name__ == "__main__":
    main()
