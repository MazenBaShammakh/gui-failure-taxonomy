#!/usr/bin/env python3
"""Streamlit browser for the GUI Agent Failure Taxonomy.

Data model (see specs/taxonomy-structure.md): failure Types are the spine,
defined in every *.yaml of taxonomy/<folder>/ except runs.yaml. How those
files are split is a per-folder convention the loader doesn't care about:
v2 splits by platform ({mobile,web,cross-platform,desktop}.yaml), v3 splits
by category (F-PRC.yaml, F-IDT.yaml, … one per category code). Real-world
evidence lives separately in taxonomy/<folder>/runs.yaml as Tasks, each holding
one or more Runs, and each Run tags 1+ Types via a `failures[]` list (a
many-to-many Run<->Type link). A type's `observed` facet values are not
stored -- they're derived here from whichever runs tag that type.

`<folder>` defaults to `v2` but is switchable from the sidebar -- any
subdirectory of taxonomy/ containing a runs.yaml is auto-detected as a
taxonomy folder (e.g. a fresh/empty `v3` for a new corpus).
"""

from collections import defaultdict
from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).parent
TAXONOMY_ROOT = ROOT / "taxonomy"
DEFAULT_TAXONOMY_FOLDER = "v2"

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
    """Subdirectories of taxonomy/ that look like a taxonomy folder (contain
    a runs.yaml) -- e.g. v2, and a fresh v3 you've started for a new corpus."""
    if not TAXONOMY_ROOT.is_dir():
        return [DEFAULT_TAXONOMY_FOLDER]
    folders = sorted(
        p.name for p in TAXONOMY_ROOT.iterdir()
        if p.is_dir() and (p / RUNS_FILE).exists()
    )
    return folders or [DEFAULT_TAXONOMY_FOLDER]


def _yaml_fingerprint(taxonomy_dir: Path) -> tuple[tuple[str, int], ...]:
    """Mtime of every taxonomy YAML file in the given folder, used as a
    cache-busting key so load_types()/load_tasks() reload whenever a file
    changes on disk (rather than only when app.py itself changes).

    Must be passed to those functions under a name that does NOT start with
    an underscore -- st.cache_data drops leading-underscore parameters from
    the cache key (its opt-out for unhashable args), which silently defeats
    the whole point of this fingerprint."""
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


@st.cache_data
def load_tasks(taxonomy_dir: Path, fingerprint: tuple[tuple[str, int], ...]) -> list[dict]:
    path = taxonomy_dir / RUNS_FILE
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def source_of(task: dict, run: dict) -> str | None:
    """`source` describes the application an attempt targeted, so it belongs
    to the Task -- it cannot differ between runs of the same task. v3 stores
    it there. v2 stored it on each Run, so fall back to that; both folders
    have to keep working."""
    return task.get("source") or run.get("source")


def build_type_index(tasks: list[dict]) -> dict[str, list[dict]]:
    """type_id -> list of {"task", "run", "edge"} dicts, one per Run that
    tags that type via its failures[] list. Order follows runs.yaml (Task
    id, then Run id), so it's stable and matches how the old schema's
    observations: list read top to bottom."""
    index: dict[str, list[dict]] = defaultdict(list)
    for task in tasks:
        for run in task.get("runs", []) or []:
            for edge in run.get("failures", []) or []:
                index[edge["type"]].append({"task": task, "run": run, "edge": edge})
    return index


def facet_values(t: dict, index: dict[str, list[dict]], facet: str) -> tuple[list[str], list[str]]:
    """Return (observed, expected) value lists for a type-level facet.
    `observed` is derived from the runs tagging this type (never stored in
    the yaml — see the module docstring); `expected` is still hand-authored."""
    entries = index.get(t["id"], [])
    observed = sorted({e["run"].get(facet) for e in entries if e["run"].get(facet)})
    expected = list((t.get("facets", {}).get(facet, {}) or {}).get("expected") or [])
    return observed, expected


def facet_chips(observed: list[str], expected: list[str]) -> str:
    chips = [f"`{v}`" for v in observed] + \
        [f"⬜ `{v}`" for v in expected if v not in observed]
    return " ".join(chips) if chips else "—"


def render_type(t: dict, index: dict[str, list[dict]], type_labels: dict[str, str]) -> None:
    category_label = CATEGORY_LABELS.get(t["category"], t["category"])
    entries = index.get(t["id"], [])
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
        st.markdown(f"Cause: {CAUSE_BADGE.get(cause, cause or '—')} (dominant case)")
        st.markdown(f"Stage: {STAGE_BADGE.get(stage, stage or '—')} (dominant case)")
        if t.get("assessment_ref"):
            st.markdown(f"Assessment ref: `{t['assessment_ref']}`")

        rep_obs, rep_exp = facet_values(t, index, "representation")
        plat_obs, plat_exp = facet_values(t, index, "platform")
        st.markdown("**Representation**")
        st.markdown(facet_chips(rep_obs, rep_exp))
        st.markdown("**Platform**")
        st.markdown(facet_chips(plat_obs, plat_exp))

    if entries:
        by_task: dict[str, dict] = {}
        for entry in entries:
            task_id = entry["task"]["id"]
            by_task.setdefault(task_id, {"task": entry["task"], "items": []})["items"].append(entry)

        n_tasks = len(by_task)
        st.markdown(f"**Observations ({n_tasks})**")
        for group in by_task.values():
            task = group["task"]
            runs_in_obs = group["items"]
            with st.container(border=True):
                st.markdown(f"`{task['id']}`  ·  App: **{task.get('app', '—')}**")
                if task.get("task"):
                    st.markdown(f"*{task['task']}*")
                caption_bits = []
                if task.get("task_id"):
                    caption_bits.append(f"Task ID: `{task['task_id']}`")
                if task.get("source"):
                    # v3: source lives on the Task, so show it once here
                    # rather than repeating it on every run card below.
                    caption_bits.append(
                        f"Source: {SOURCE_BADGE.get(task['source'], task['source'])}")
                if len(runs_in_obs) > 1:
                    caption_bits.append(f"{len(runs_in_obs)} runs recorded")
                if caption_bits:
                    st.caption("  ·  ".join(caption_bits))

                for entry in runs_in_obs:
                    run, edge = entry["run"], entry["edge"]
                    with st.container(border=True):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            # run_id is the harness's own id for the execution
                            # (v3 onward, absent in v2) -- the pointer back to
                            # the raw trace. Rendered as-is on purpose: one
                            # written with a `T`/space separator instead of `_`
                            # parses as a datetime, and showing YAML's
                            # reformatting of it is the tell that it's wrong.
                            harness_id = run.get("run_id")
                            st.markdown(
                                f"`{run['id']}`"
                                + (f"  :gray[{harness_id}]" if harness_id else "")
                                + ("  :gray[(unverified)]" if run.get("verified") is False else ""))
                            if run.get("notes"):
                                st.caption(run["notes"].strip())
                            other_types = [f for f in run.get("failures", []) if f["type"] != t["id"]]
                            if other_types:
                                others = ", ".join(
                                    f"`{f['type']}` ({type_labels.get(f['type'], f['type'])})"
                                    for f in other_types
                                )
                                st.caption(f"Same run also evidences: {others}")
                        with c2:
                            st.markdown(
                                f"{run.get('representation', '—')} · {run.get('platform', '—')}"
                            )
                            st.markdown(OUTCOME_BADGE.get(
                                run.get("outcome"), run.get("outcome", "—")))
                            if run.get("source") and not task.get("source"):
                                # v2 only -- v3 shows it on the task caption.
                                st.markdown(
                                    f"Source: {SOURCE_BADGE.get(run['source'], run['source'])}")
                            if run.get("route"):
                                st.markdown(f"Route: `{run['route']}`")
                            edge_cause, edge_stage = edge.get("cause"), edge.get("stage")
                            if (edge_cause, edge_stage) != (cause, stage):
                                st.caption(
                                    f"This run: {CAUSE_BADGE.get(edge_cause, edge_cause or '—')} · "
                                    f"{STAGE_BADGE.get(edge_stage, edge_stage or '—')}"
                                )
    else:
        st.info("No logged runs — predicted / expected only.")


def main() -> None:
    st.set_page_config(page_title="GUI Failure Taxonomy",
                       page_icon="🔍", layout="wide")

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
            help="Which taxonomy/<folder> to browse. Auto-detected: any "
                 "subfolder of taxonomy/ containing a runs.yaml (e.g. a "
                 "fresh, empty folder started for a new corpus).",
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
            format_func=lambda c: CATEGORY_LABELS.get(c, c),
            help="Filters on each type's `category` field. In a v3 folder "
                 "that is 1:1 with its source file (F-PRC.yaml, …); in v2, "
                 "files are platforms and cut across categories.",
        )
        sel_causes = st.multiselect("Cause", all_causes, default=all_causes)
        sel_stages = st.multiselect("Stage", all_stages, default=all_stages)

        st.divider()
        sel_reps = st.multiselect(
            "Representation", REPRESENTATIONS, default=REPRESENTATIONS)
        sel_plats = st.multiselect("Platform", PLATFORMS, default=PLATFORMS)
        observed_only = st.checkbox(
            "Observed only (exclude expected-only matches)", value=False,
            help="When on, a type must have the selected representation/platform in its derived OBSERVED set, not just expected.",
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
            "Auto-refresh",
            value=st.query_params.get("autorefresh") == "1",
            help="Streamlit's dev-mode file watcher only tracks .py files, not "
                 "taxonomy/v2/*.yaml, so editing a YAML doesn't trigger a rerun "
                 "on its own — turn this on to reload the page on an interval "
                 "instead of refreshing the browser tab by hand. Uses a full "
                 "page reload, so the setting is round-tripped through the URL "
                 "(?autorefresh=1&interval=N) to survive it.",
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

    def entries_for(t: dict) -> list[dict]:
        return index.get(t["id"], [])

    def observation_count(t: dict) -> int:
        """Number of distinct Tasks evidencing this type. A Task with
        multiple Runs (e.g. the classic VO-fails/MM-succeeds contrast) is
        one observation, not one per run — an observation is derived from
        the Task, not the Run."""
        return len({e["task"]["id"] for e in entries_for(t)})

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Types", len(filtered))
    m2.metric("Observations", sum(observation_count(t) for t in filtered))
    m3.metric("With observations", sum(1 for t in filtered if entries_for(t)))
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
        n_obs = sum(observation_count(t) for t in group)
        n_with_evidence = sum(1 for t in group if entries_for(t))

        st.markdown(
            f"## {category_label}  ·  {n_types} types  ·  "
            f"{n_obs} observation{'s' if n_obs != 1 else ''}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Types", n_types)
        c2.metric("Observations", n_obs)
        c3.metric("With observations", n_with_evidence)
        st.divider()

        for t in group:
            n_obs_t = observation_count(t)
            badge = f"({n_obs_t} observation{'s' if n_obs_t != 1 else ''})" if n_obs_t else "(predicted only)"
            # In a category-per-file folder the source file is just the
            # section header again, so only show it when it says something
            # the header doesn't (v2: the platform the type lives under).
            origin = ("" if t["_source_file"] in CODE_TO_CATEGORY
                      else f"{t['_source_file']}  ")
            label = (
                f"{t['id']}  ·  {t['failure'].replace('_', ' ')}  ·  "
                f"{origin}{badge}"
            )
            with st.expander(label, expanded=False):
                render_type(t, index, type_labels)

        st.divider()


if __name__ == "__main__":
    main()
