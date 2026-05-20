#!/usr/bin/env python3
"""Generate Mermaid mindmap diagrams from taxonomy YAML files.

Outputs:
  output/diagrams/taxonomy_full.mmd          — all platforms combined
  output/diagrams/taxonomy_{platform}.mmd    — one per platform
"""

from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
TAXONOMY_DIR = ROOT / "taxonomy"
OUTPUT_DIR = ROOT / "output" / "diagrams"
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


def build_tree(entries: list[dict]) -> dict:
    tree: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for e in entries:
        tree[e["platform"]][e["agent_type"]][e["category"]].append(e["failure"])
    return tree


def _escape(text: str) -> str:
    return text.replace('"', "'")


def _failure_label(snake: str) -> str:
    return _escape(snake.replace("_", " ").title())


def _agent_section(agent: str, categories: dict, indent: int) -> list[str]:
    pad = "  " * indent
    lines = [f"{pad}{AGENT_LABELS[agent]}"]
    for cat in sorted(categories):
        lines.append(f"{pad}  {CATEGORY_LABELS.get(cat, cat)}")
        for failure in categories[cat]:
            lines.append(f"{pad}    {_failure_label(failure)}")
    return lines


def mindmap_full(tree: dict) -> str:
    lines = ["mindmap", "  root((GUI Agent Failures))"]
    for platform in sorted(tree):
        lines.append(f"    {PLATFORM_LABELS[platform]}")
        for agent in sorted(tree[platform]):
            lines.extend(_agent_section(agent, tree[platform][agent], indent=3))
    return "\n".join(lines)


def mindmap_platform(platform: str, agents: dict) -> str:
    lines = ["mindmap", f"  root(({PLATFORM_LABELS[platform]}))"]
    for agent in sorted(agents):
        lines.extend(_agent_section(agent, agents[agent], indent=2))
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_entries()
    tree = build_tree(entries)

    full_path = OUTPUT_DIR / "taxonomy_full.mmd"
    full_path.write_text(mindmap_full(tree), encoding="utf-8")
    print(f"Written: {full_path.relative_to(ROOT)}")

    for platform, agents in sorted(tree.items()):
        slug = platform.replace("-", "_")
        out = OUTPUT_DIR / f"taxonomy_{slug}.mmd"
        out.write_text(mindmap_platform(platform, agents), encoding="utf-8")
        print(f"Written: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
