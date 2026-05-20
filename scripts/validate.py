#!/usr/bin/env python3
"""Validate all taxonomy YAML files against schemas/entry.schema.json."""

import json
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).parent.parent
TAXONOMY_DIR = ROOT / "taxonomy"
SCHEMA_FILE = ROOT / "schemas" / "entry.schema.json"
SKIP = {"schema.yaml"}


def main() -> None:
    with SCHEMA_FILE.open() as f:
        schema = json.load(f)

    yaml_files = sorted(p for p in TAXONOMY_DIR.glob("*.yaml") if p.name not in SKIP)
    if not yaml_files:
        print("No taxonomy files found.", file=sys.stderr)
        sys.exit(1)

    errors: list[str] = []
    for path in yaml_files:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None or data == []:
            print(f"  SKIP  {path.name}  (empty)")
            continue

        try:
            jsonschema.validate(data, schema)
            print(f"  OK    {path.name}  ({len(data)} entries)")
        except jsonschema.ValidationError as e:
            loc = " > ".join(str(p) for p in e.absolute_path) or "(root)"
            errors.append(f"{path.name} [{loc}]: {e.message}")
            print(f"  FAIL  {path.name}")

    if errors:
        print("\nValidation errors:")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)

    print("\nAll files valid.")


if __name__ == "__main__":
    main()
