#!/usr/bin/env python3
"""Pull Clay Audiences config into git-diffable files.

Layout:
  audiences/fields/<entity-type>.json   field definitions for that entity type
  audiences/segments/<slug>.json        one saved audience (segment) per file

This only ever touches config, never records or activities. Records and
activities are data, not config, and stay out of git the same way workflow
*runs* aren't versioned, only the workflow *definition* is.

Run this twice with no live edits in between and the git diff should be empty.
"""
import json, re, subprocess, pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
ENTITY_TYPES = ["people", "companies"]  # deals has no saved-audience surface
VOLATILE_KEYS = {"createdAt", "updatedAt"}

def sh(args):
    out = subprocess.run(["clay"] + args, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"clay {' '.join(args)}: {out.stderr[:400]}")
    return json.loads(out.stdout)

def slugify(name):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")

def canonical(obj):
    return {k: v for k, v in obj.items() if k not in VOLATILE_KEYS and v is not None}

def pull_fields():
    out_dir = REPO / "audiences" / "fields"
    out_dir.mkdir(parents=True, exist_ok=True)
    for entity_type in ENTITY_TYPES:
        fields = sh(["audiences", "fields", "list", "--entity-type", entity_type])["data"]
        fields = sorted((canonical(f) for f in fields), key=lambda f: f["id"])
        (out_dir / f"{entity_type}.json").write_text(json.dumps(fields, indent=2, sort_keys=True) + "\n")
        print(f"pulled {len(fields)} {entity_type} fields -> audiences/fields/{entity_type}.json")

def pull_segments():
    out_dir = REPO / "audiences" / "segments"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()
    for entity_type in ENTITY_TYPES:
        cursor = None
        while True:
            args = ["audiences", "list", "--entity-type", entity_type]
            if cursor:
                args += ["--cursor", cursor]
            page = sh(args)
            for row in page["data"]:
                full = sh(["audiences", "get", row["id"]])
                slug = slugify(full["name"])
                (out_dir / f"{slug}.json").write_text(json.dumps(canonical(full), indent=2, sort_keys=True) + "\n")
                print(f"pulled segment {full['name']!r} -> audiences/segments/{slug}.json")
            cursor = page.get("cursor")
            if not cursor:
                break

if __name__ == "__main__":
    pull_fields()
    pull_segments()
