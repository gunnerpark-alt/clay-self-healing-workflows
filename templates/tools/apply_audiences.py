#!/usr/bin/env python3
"""Apply repo Audiences config (fields + segments) back to Clay.

Fields: diff each entity type's file against `fields list`; update changed
ones. Creating a field from the repo isn't automated here — run
`clay audiences fields create` by hand, then re-run pull_audiences.py to pick
up the new id. Deleting a field is never automatic either; it destroys data
on every record, so that stays a deliberate, separate action.

Segments: diff each file against `clay audiences get <id>`; update changed
ones, create new ones (a file with no "id" yet). A segment file removed from
the repo is left alone in Clay, not archived — same reasoning as fields.

Dry-run by default. Pass --write to execute.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pull_audiences import sh, canonical, REPO, ENTITY_TYPES

FIELD_WRITABLE = {"name", "description", "dataType", "hidden", "order"}
FIELD_FLAG_NAME = {"dataType": "data-type"}

def apply_fields(write):
    for entity_type in ENTITY_TYPES:
        path = REPO / "audiences" / "fields" / f"{entity_type}.json"
        if not path.exists():
            continue
        repo_fields = {f["id"]: f for f in json.loads(path.read_text()) if f.get("id")}
        live_fields = {f["id"]: canonical(f)
                       for f in sh(["audiences", "fields", "list", "--entity-type", entity_type])["data"]}

        plan = []
        for fid, field in repo_fields.items():
            live = live_fields.get(fid)
            if not live:
                continue  # unknown id — pull_audiences.py again rather than guessing
            diff = {k: v for k, v in field.items()
                    if k in FIELD_WRITABLE
                    and json.dumps(live.get(k), sort_keys=True) != json.dumps(v, sort_keys=True)}
            if diff:
                plan.append((fid, field.get("name", fid), diff))

        print(f"\n== {entity_type} fields — {len(plan)} update(s) ==")
        for fid, name, diff in plan:
            print(f"  update {name} fields: {sorted(diff)}")
        if not write:
            continue
        for fid, name, diff in plan:
            args = ["audiences", "fields", "update", fid, "--entity-type", entity_type]
            for k, v in diff.items():
                args += [f"--{FIELD_FLAG_NAME.get(k, k)}", v if isinstance(v, str) else json.dumps(v)]
            sh(args)
            print(f"  applied: update {name}")

def apply_segments(write):
    seg_dir = REPO / "audiences" / "segments"
    if not seg_dir.exists():
        return
    plan = []
    for path in sorted(seg_dir.glob("*.json")):
        seg = json.loads(path.read_text())
        sid = seg.get("id")
        if not sid:
            plan.append(("create", None, seg))
            continue
        live = canonical(sh(["audiences", "get", sid]))
        diff = {k: v for k, v in seg.items() if k in ("name", "description", "filter")
                and json.dumps(live.get(k), sort_keys=True) != json.dumps(v, sort_keys=True)}
        if diff:
            plan.append(("update", sid, seg))

    print(f"\n== segments — {len(plan)} operation(s) ==")
    for op, sid, seg in plan:
        print(f"  {op:6} {seg['name']}")
    if not write:
        return
    for op, sid, seg in plan:
        if op == "create":
            created = sh(["audiences", "create", "--entity-type", seg["entityType"], "--name", seg["name"]])
            sh(["audiences", "update", created["id"], "--filter", json.dumps(seg["filter"])])
            print(f"  applied: create {seg['name']} -> {created['id']} (re-run pull_audiences.py to pick up the id)")
        else:
            args = ["audiences", "update", sid]
            if seg.get("name"): args += ["--name", seg["name"]]
            if seg.get("description") is not None: args += ["--description", seg["description"]]
            if seg.get("filter"): args += ["--filter", json.dumps(seg["filter"])]
            sh(args)
            print(f"  applied: update {seg['name']}")

if __name__ == "__main__":
    write = "--write" in sys.argv
    apply_fields(write)
    apply_segments(write)
