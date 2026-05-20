#!/usr/bin/env python3
"""Generate a Markdown summary table from taxonomy YAML files.

Output: output/summary.md
"""

from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
TAXONOMY_DIR = ROOT / "taxonomy"
OUTPUT_FILE = ROOT / "output" / "summary.md"
SKIP = {"schema.yaml"}

PLATFORM_LABELS = {
    "web": "Web",
    "mobile": "Mobile",
    "desktop": "Desktop",
    "cross-platform": "Cross-platform",
}
AGENT_LABELS = {
    "vision-only": "Vision-only",
    "multimodal": "Multimodal",
}
CATEGORY_LABELS = {
    "visual_vs_structural":       "Visual vs Structural",
    "accessibility_semantics":    "Accessibility & Semantics",
    "gestures":                   "Gestures",
    "content_layout":             "Content & Layout",
    "navigation_flow":            "Navigation & Flow",
    "forms_validations_feedback": "Forms / Validations / Feedback",
    "visual_affordance":          "Visual Affordance",
    "action_affordance":          "Action Affordance",
}


def load_entries() -> list[dict]:
    entries = []
    for path in sorted(TAXONOMY_DIR.glob("*.yaml")):
        if path.name in SKIP:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data:
            entries.extend(data)
    return entries


def main() -> None:
    entries = load_entries()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    tree: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for e in entries:
        tree[e["platform"]][e["agent_type"]][e["category"]].append(e)

    lines = [
        "# GUI Agent Failure Taxonomy — Summary",
        "",
        f"_Auto-generated. Total entries: {len(entries)}_",
        "",
    ]

    for platform in sorted(tree):
        lines.append(f"## {PLATFORM_LABELS[platform]}")
        lines.append("")
        for agent in sorted(tree[platform]):
            lines.append(f"### {AGENT_LABELS[agent]}")
            lines.append("")
            for category in sorted(tree[platform][agent]):
                cat_entries = sorted(tree[platform][agent][category], key=lambda x: x["id"])
                lines.append(f"#### {CATEGORY_LABELS.get(category, category)}")
                lines.append("")
                lines.append("| ID | Failure | Cause | Stage |")
                lines.append("|----|---------|-------|-------|")
                for e in cat_entries:
                    label = e["failure"].replace("_", " ")
                    lines.append(f"| `{e['id']}` | {label} | {e['cause']} | {e['stage']} |")
                lines.append("")
                for e in cat_entries:
                    lines.append(f"**`{e['id']}`** — {e['description'].strip()}")
                    lines.append("")

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {OUTPUT_FILE.relative_to(ROOT)}  ({len(entries)} entries)")


if __name__ == "__main__":
    main()
