#!/usr/bin/env python3
"""Compiles registry manifests into optimized index feeds for Theta Hub."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def build_index(registry_dir: Path, output_dir: Path) -> dict:
    components = []
    seen_ids = set()

    # Search registry/**/*.json
    for json_file in sorted(registry_dir.rglob("*.json")):
        # Skip hidden files or schemas
        if json_file.name.startswith(".") or "schemas" in json_file.parts:
            continue

        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"ERROR: Failed to parse {json_file}: {exc}", file=sys.stderr)
            sys.exit(1)

        comp_id = data.get("id")
        if not comp_id:
            print(f"ERROR: Missing 'id' in {json_file}", file=sys.stderr)
            sys.exit(1)

        if comp_id in seen_ids:
            print(f"ERROR: Duplicate component id '{comp_id}' found in {json_file}", file=sys.stderr)
            sys.exit(1)

        seen_ids.add(comp_id)
        components.append(data)

    components.sort(key=lambda c: (c.get("kind", ""), c.get("id", "")))

    now_iso = datetime.now(timezone.utc).isoformat()
    manifest_index = {
        "$schema": "https://hub.thetaide.org/schemas/component-v1.json",
        "version": "1.0",
        "updated_at": now_iso,
        "count": len(components),
        "components": components,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Full readable index.json
    index_file = output_dir / "index.json"
    index_file.write_text(json.dumps(manifest_index, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {index_file} ({len(components)} components)")

    # 2. Minified index.min.json for fast network downloads
    min_file = output_dir / "index.min.json"
    min_file.write_text(json.dumps(manifest_index, separators=(",", ":")), encoding="utf-8")
    print(f"Generated minified {min_file}")

    # 3. Category sub-indices
    categories_dir = output_dir / "categories"
    categories_dir.mkdir(exist_ok=True)
    by_kind = {}
    for c in components:
        k = c.get("kind", "other")
        by_kind.setdefault(k, []).append(c)

    for kind, items in by_kind.items():
        kind_file = categories_dir / f"{kind}.json"
        kind_data = {
            "kind": kind,
            "updated_at": now_iso,
            "count": len(items),
            "components": items,
        }
        kind_file.write_text(json.dumps(kind_data, indent=2) + "\n", encoding="utf-8")
        print(f"Generated category feed: {kind_file} ({len(items)} items)")

    return manifest_index


def main():
    parser = argparse.ArgumentParser(description="Compile Theta Hub registry into index feeds.")
    parser.add_argument(
        "--registry-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "registry",
        help="Path to registry directory containing component json files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "dist",
        help="Path to output directory where index feeds will be written",
    )
    args = parser.parse_args()

    build_index(args.registry_dir, args.output_dir)


if __name__ == "__main__":
    main()
