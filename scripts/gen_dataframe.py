#!/usr/bin/env python3
"""Flatten taxonomy YAML files into a pandas DataFrame and write output/taxonomy.csv."""

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).parent.parent
TAXONOMY_DIR = ROOT / "taxonomy"
OUTPUT_FILE = ROOT / "output" / "taxonomy.csv"
SKIP = {"schema.yaml"}

COLUMNS = ["id", "platform", "agent_type", "category", "failure",
           "description", "cause", "stage", "example_count"]


def load_entries() -> list[dict]:
    entries = []
    for path in sorted(TAXONOMY_DIR.glob("*.yaml")):
        if path.name in SKIP:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data:
            entries.extend(data)
    return entries


def flatten(e: dict) -> dict:
    return {
        "id":            e["id"],
        "platform":      e["platform"],
        "agent_type":    e["agent_type"],
        "category":      e["category"],
        "failure":       e["failure"],
        "description":   e.get("description", "").strip(),
        "cause":         e["cause"],
        "stage":         e["stage"],
        "example_count": len(e.get("examples", [])),
    }


def main() -> None:
    entries = load_entries()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([flatten(e) for e in entries], columns=COLUMNS) if entries \
        else pd.DataFrame(columns=COLUMNS)

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Written: {OUTPUT_FILE.relative_to(ROOT)}  ({len(df)} rows)")

    if not df.empty:
        for col in ("platform", "agent_type", "category", "cause", "stage"):
            print(f"\n{col}:\n{df[col].value_counts().to_string()}")


if __name__ == "__main__":
    main()
