#!/usr/bin/env python3
"""Streamlit browser for the GUI Agent Failure Taxonomy."""

import yaml
import streamlit as st
from pathlib import Path

ROOT = Path(__file__).parent
TAXONOMY_DIR = ROOT / "taxonomy"
SKIP = {"schema.yaml"}

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


@st.cache_data
def load_entries() -> list[dict]:
    entries = []
    for path in sorted(TAXONOMY_DIR.glob("*.yaml")):
        if path.name in SKIP:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data:
            entries.extend(data)
    return entries


def render_entry(e: dict) -> None:
    examples = e.get("examples", [])
    category_label = CATEGORY_LABELS.get(e["category"], e["category"])

    left, right = st.columns([3, 1])

    with left:
        st.markdown(f"#### {e['failure'].replace('_', ' ')}")
        st.write(e.get("description", "").strip())

    with right:
        st.markdown("**Attributes**")
        st.markdown(f"Platform: `{e['platform']}`")
        st.markdown(f"Agent: `{e['agent_type']}`")
        st.markdown(f"Category: `{category_label}`")
        st.markdown(f"Cause: {CAUSE_BADGE.get(e['cause'], e['cause'])}")
        st.markdown(f"Stage: {STAGE_BADGE.get(e['stage'], e['stage'])}")
        if e.get("assessment_ref"):
            st.markdown(f"Assessment ref: `{e['assessment_ref']}`")

    if examples:
        st.markdown(f"**Observations ({len(examples)})**")
        for ex in examples:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"`{ex['scenario_id']}`")
                    if ex.get("task"):
                        st.markdown(f"*{ex['task']}*")
                    if ex.get("notes"):
                        st.caption(ex["notes"].strip())
                with c2:
                    st.markdown(f"App: **{ex['app']}**")
                    st.markdown(f"Source: {SOURCE_BADGE.get(ex['source'], ex['source'])}")
                    if ex.get("route"):
                        st.markdown(f"Route: `{ex['route']}`")


def main() -> None:
    st.set_page_config(
        page_title="GUI Failure Taxonomy",
        page_icon="🔍",
        layout="wide",
    )

    st.title("GUI Agent Failure Taxonomy")
    st.caption("Browse and filter documented GUI agent failure patterns.")

    entries = load_entries()

    # ── Sidebar Filters ──────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Filters")

        all_platforms  = sorted({e["platform"]   for e in entries})
        all_agents     = sorted({e["agent_type"] for e in entries})
        all_categories = sorted({e["category"]   for e in entries})
        all_causes     = sorted({e["cause"]      for e in entries})
        all_stages     = sorted({e["stage"]      for e in entries})

        sel_platforms  = st.multiselect("Platform",   all_platforms,  default=all_platforms)
        sel_agents     = st.multiselect("Agent type", all_agents,     default=all_agents)
        sel_categories = st.multiselect("Category",   all_categories, default=all_categories)
        sel_causes     = st.multiselect("Cause",      all_causes,     default=all_causes)
        sel_stages     = st.multiselect("Stage",      all_stages,     default=all_stages)

        st.divider()
        search = st.text_input("Search", placeholder="failure name or description…")

    # ── Apply Filters ────────────────────────────────────────────────────────
    q = search.strip().lower()
    filtered = [
        e for e in entries
        if e["platform"]   in sel_platforms
        and e["agent_type"] in sel_agents
        and e["category"]   in sel_categories
        and e["cause"]      in sel_causes
        and e["stage"]      in sel_stages
        and (
            not q
            or q in e["failure"].lower()
            or q in e.get("description", "").lower()
            or q in e["id"].lower()
        )
    ]

    # ── Summary Metrics ──────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Entries",    len(filtered))
    m2.metric("With observations", sum(1 for e in filtered if e.get("examples")))
    m3.metric("Platforms",  len({e["platform"]  for e in filtered}))
    m4.metric("Categories", len({e["category"]  for e in filtered}))
    m5.metric("Agent types", len({e["agent_type"] for e in filtered}))

    st.divider()

    # ── Entry Cards ──────────────────────────────────────────────────────────
    if not filtered:
        st.info("No entries match the current filters.")
        return

    for e in filtered:
        category_label = CATEGORY_LABELS.get(e["category"], e["category"])
        n_examples = len(e.get("examples", []))
        badge = f"({n_examples} obs.)" if n_examples else ""

        label = (
            f"**{e['id']}** &nbsp;·&nbsp; "
            f"`{e['platform']}` &nbsp;·&nbsp; "
            f"`{e['agent_type']}` &nbsp;·&nbsp; "
            f"`{category_label}` &nbsp; {badge}"
        )

        with st.expander(
            f"{e['id']}  ·  {e['failure'].replace('_', ' ')}  ·  {category_label}  {badge}"
        ):
            render_entry(e)


if __name__ == "__main__":
    main()
