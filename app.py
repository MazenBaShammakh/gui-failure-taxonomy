#!/usr/bin/env python3
"""Streamlit browser for the GUI Agent Failure Taxonomy (v2)."""

from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).parent
TAXONOMY_V2_DIR = ROOT / "taxonomy" / "v2"

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

FILE_LABELS = {
    "mobile": "mobile",
    "web": "web",
    "cross-platform": "cross-platform",
    "desktop": "desktop",
}


def _yaml_fingerprint() -> tuple[tuple[str, int], ...]:
    """Mtime of every taxonomy YAML file, used as a cache-busting key so
    load_types() reloads whenever a file changes on disk (rather than only
    when app.py itself changes)."""
    return tuple(
        (path.name, path.stat().st_mtime_ns)
        for path in sorted(TAXONOMY_V2_DIR.glob("*.yaml"))
    )


@st.cache_data
def load_types(_fingerprint: tuple[tuple[str, int], ...]) -> list[dict]:
    types = []
    for path in sorted(TAXONOMY_V2_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not data:
            continue
        source_file = FILE_LABELS.get(path.stem, path.stem)
        for t in data:
            t = dict(t)
            t["_source_file"] = source_file
            t.setdefault("observations", [])
            types.append(t)
    return types


def facet_values(t: dict, facet: str) -> tuple[list[str], list[str]]:
    """Return (observed, expected) value lists for a type-level facet."""
    f = t.get("facets", {}).get(facet, {}) or {}
    return list(f.get("observed") or []), list(f.get("expected") or [])


def facet_chips(observed: list[str], expected: list[str]) -> str:
    chips = [f"`{v}`" for v in observed] + \
        [f"⬜ `{v}`" for v in expected if v not in observed]
    return " ".join(chips) if chips else "—"


def render_type(t: dict) -> None:
    category_label = CATEGORY_LABELS.get(t["category"], t["category"])
    obs = t.get("observations", [])
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
        st.markdown(f"Cause: {CAUSE_BADGE.get(cause, cause or '—')}")
        st.markdown(f"Stage: {STAGE_BADGE.get(stage, stage or '—')}")
        if t.get("assessment_ref"):
            st.markdown(f"Assessment ref: `{t['assessment_ref']}`")

        rep_obs, rep_exp = facet_values(t, "representation")
        plat_obs, plat_exp = facet_values(t, "platform")
        st.markdown("**Representation**")
        st.markdown(facet_chips(rep_obs, rep_exp))
        st.markdown("**Platform**")
        st.markdown(facet_chips(plat_obs, plat_exp))

    if obs:
        st.markdown(f"**Observations ({len(obs)})**")
        for ob in obs:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(
                        f"`{ob['id']}`" + ("  :gray[(unverified)]" if ob.get("verified") is False else ""))
                    if ob.get("task"):
                        st.markdown(f"*{ob['task']}*")
                    if ob.get("notes"):
                        st.caption(ob["notes"].strip())
                with c2:
                    st.markdown(f"App: **{ob.get('app', '—')}**")
                    st.markdown(
                        f"{ob.get('representation', '—')} · {ob.get('platform', '—')}"
                    )
                    st.markdown(OUTCOME_BADGE.get(
                        ob.get("outcome"), ob.get("outcome", "—")))
                    st.markdown(
                        f"Source: {SOURCE_BADGE.get(ob.get('source'), ob.get('source', '—'))}")
                    if ob.get("route"):
                        st.markdown(f"Route: `{ob['route']}`")
    else:
        st.info("No logged observations — predicted / expected only.")


def main() -> None:
    st.set_page_config(page_title="GUI Failure Taxonomy (v2)",
                       page_icon="🔍", layout="wide")

    st.title("GUI Failure Taxonomy")
    st.caption(
        "Browse the type/observation taxonomy in `taxonomy/v2/`. "
        "Types are Category → Failure (spine); Representation, Platform, "
        "Cause, and Stage are facets."
    )

    types = load_types(_yaml_fingerprint())

    with st.sidebar:
        st.header("Filters")

        all_files = sorted({t["_source_file"] for t in types})
        all_causes = sorted({t.get("facets", {}).get("cause")
                            for t in types if t.get("facets", {}).get("cause")})
        all_stages = sorted({t.get("facets", {}).get("stage")
                            for t in types if t.get("facets", {}).get("stage")})
        all_sources = sorted({ob.get("source") for t in types for ob in t.get(
            "observations", []) if ob.get("source")})
        all_outcomes = sorted({ob.get("outcome") for t in types for ob in t.get(
            "observations", []) if ob.get("outcome")})

        sel_files = st.multiselect("File", all_files, default=all_files)
        sel_causes = st.multiselect("Cause", all_causes, default=all_causes)
        sel_stages = st.multiselect("Stage", all_stages, default=all_stages)

        st.divider()
        sel_reps = st.multiselect(
            "Representation", REPRESENTATIONS, default=REPRESENTATIONS)
        sel_plats = st.multiselect("Platform", PLATFORMS, default=PLATFORMS)
        observed_only = st.checkbox(
            "Observed only (exclude expected-only matches)", value=False,
            help="When on, a type must have the selected representation/platform in its OBSERVED set, not just expected.",
        )

        st.divider()
        sel_sources = st.multiselect(
            "Observation source", all_sources, default=all_sources)
        sel_outcomes = st.multiselect(
            "Observation outcome", all_outcomes, default=all_outcomes)

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
        if t["_source_file"] not in sel_files:
            return False
        cause = t.get("facets", {}).get("cause")
        if cause not in sel_causes:
            return False
        stage = t.get("facets", {}).get("stage")
        if stage not in sel_stages:
            return False

        rep_obs, rep_exp = facet_values(t, "representation")
        rep_pool = rep_obs if observed_only else set(rep_obs) | set(rep_exp)
        if not (set(rep_pool) & set(sel_reps)):
            return False

        plat_obs, plat_exp = facet_values(t, "platform")
        plat_pool = plat_obs if observed_only else set(
            plat_obs) | set(plat_exp)
        if not (set(plat_pool) & set(sel_plats)):
            return False

        obs = t.get("observations", [])
        if obs:
            if not any(ob.get("source") in sel_sources for ob in obs):
                return False
            if not any(ob.get("outcome") in sel_outcomes for ob in obs):
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

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Types", len(filtered))
    m2.metric("Observations", sum(len(t.get("observations", []))
              for t in filtered))
    m3.metric("With observations", sum(
        1 for t in filtered if t.get("observations")))
    m4.metric("Categories", len({t["category"] for t in filtered}))
    m5.metric("Files", len({t["_source_file"] for t in filtered}))

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
        n_obs = sum(len(t.get("observations", [])) for t in group)
        n_with_obs = sum(1 for t in group if t.get("observations"))

        st.markdown(
            f"## {category_label}  ·  {n_types} types  ·  {n_obs} obs.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Types", n_types)
        c2.metric("Observations", n_obs)
        c3.metric("With observations", n_with_obs)
        st.divider()

        for t in group:
            n_obs_t = len(t.get("observations", []))
            badge = f"({n_obs_t} obs.)" if n_obs_t else "(predicted only)"
            label = (
                f"{t['id']}  ·  {t['failure'].replace('_', ' ')}  ·  "
                f"{t['_source_file']}  {badge}"
            )
            with st.expander(label, expanded=False):
                render_type(t)

        st.divider()


if __name__ == "__main__":
    main()
