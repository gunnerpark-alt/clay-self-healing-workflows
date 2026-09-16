#!/usr/bin/env python3
"""Apply repo workflow state back to Clay, node by node.

For each workflow dir given (or all under workflows/):
  1. read repo state (workflow.json, re-inlining .prompt.md / .py files)
  2. read live state via `clay workflows graph get --mode full`, canonicalized identically
  3. diff per node id:
       changed fields -> clay workflows nodes update (only the changed fields)
       repo node without id -> clay workflows nodes create
       live node missing from repo -> clay workflows nodes delete
  4. clay workflows graph validate
  5. --publish to publish the draft as live

Dry-run by default: prints the operation plan. Pass --write to execute, and
--publish to also publish once the graph validates.
"""
import json, pathlib, subprocess, sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from pull_workflows import sh, canonical_node, normalize_platform_noise  # reuse canonicalization

# Fields that are part of the graph model but not writable per-node via nodes update.
# Edges are written on the TARGET node as incomingEdges [{"sourceNode", "ruleId"/"isDefaultRoute"}];
# outgoingEdges is the derived mirror — nodes update rejects it.
NON_WRITABLE = {"id", "agentPromptFile", "codeFile", "outgoingEdges"}


def shorthand_output_schema(schema):
    """The read surface returns full JSON Schema; the write surface only accepts
    the flat {field: {type, description}} shorthand. Convert on write."""
    if not isinstance(schema, dict) or "properties" not in schema:
        return schema
    ALLOWED = {"string", "number", "boolean", "email", "url", "select"}
    out = {}
    for name, prop in schema["properties"].items():
        t = prop.get("type", "string")
        out[name] = {"type": t if t in ALLOWED else "string",
                     "description": prop.get("description", name)}
    return out

def load_repo(wf_dir):
    doc = json.loads((wf_dir / "workflow.json").read_text())
    for node in doc["nodes"]:
        normalize_platform_noise(node)  # match canonical_node
        pf = node.pop("agentPromptFile", None)
        if pf:
            node["agentPrompt"] = (wf_dir / pf).read_text().rstrip()
        cf = node.pop("codeFile", None)
        if cf:
            node["code"] = (wf_dir / cf).read_text().rstrip()
    return doc

def load_live(wf_id, scratch):
    graph = sh(["workflows", "graph", "get", wf_id, "--mode", "full"])
    nodes = {}
    for raw in sorted(graph.get("nodes") or [], key=lambda n: n["id"]):
        n = canonical_node(raw, scratch)
        pf = n.pop("agentPromptFile", None)
        if pf:
            n["agentPrompt"] = (scratch / pathlib.Path(pf).name).read_text().rstrip()
        cf = n.pop("codeFile", None)
        if cf:
            n["code"] = (scratch / pathlib.Path(cf).name).read_text().rstrip()
        nodes[raw["id"]] = n
    return nodes

def changed_fields(repo_node, live_node):
    diff = {}
    for key, value in repo_node.items():
        if key in NON_WRITABLE:
            continue
        if json.dumps(live_node.get(key), sort_keys=True) != json.dumps(value, sort_keys=True):
            diff[key] = value
    return diff

def apply_workflow(wf_dir, write=False, publish=False):
    repo_doc = load_repo(wf_dir)
    wf_id = repo_doc["workflowId"]
    scratch = pathlib.Path("/tmp/apply-scratch"); scratch.mkdir(exist_ok=True)
    live = load_live(wf_id, scratch)

    plan = []
    repo_ids = set()
    for node in repo_doc["nodes"]:
        nid = node.get("id")
        if nid and nid in live:
            repo_ids.add(nid)
            diff = changed_fields(node, live[nid])
            if diff:
                plan.append(("update", nid, node.get("name", nid), diff))
        else:
            plan.append(("create", None, node.get("name", "?"),
                         {k: v for k, v in node.items() if k not in ("id",)}))
    for nid, node in live.items():
        if node.get("nodeType") != "trigger" and nid not in repo_ids:
            plan.append(("delete", nid, node.get("name", nid), None))

    print(f"\n== {repo_doc['workflowName']} ({wf_id}) — {len(plan)} operation(s) ==")
    for op, nid, name, diff in plan:
        detail = f" fields: {sorted(diff)}" if isinstance(diff, dict) else ""
        print(f"  {op:6} {name}{detail}")
    if not write or not plan:
        return
    for op, nid, name, diff in plan:
        if op == "update":
            if "outputSchema" in diff:
                diff["outputSchema"] = shorthand_output_schema(diff["outputSchema"])
            sh(["workflows", "nodes", "update", wf_id, nid, "--input", json.dumps(diff)])
        elif op == "create":
            if "outputSchema" in diff:
                diff["outputSchema"] = shorthand_output_schema(diff["outputSchema"])
            sh(["workflows", "nodes", "create", wf_id, "--input", json.dumps(diff)])
        elif op == "delete":
            sh(["workflows", "nodes", "delete", wf_id, nid])
        print(f"  applied: {op} {name}")
    verdict = sh(["workflows", "graph", "validate", wf_id])
    print(f"  validate: valid={verdict.get('valid')} errors={len(verdict.get('errors', []))}")
    if publish and verdict.get("valid"):
        version = sh(["workflows", "publish", wf_id])
        print(f"  published v{version['publishedVersion']['number']}")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write = "--write" in sys.argv
    publish = "--publish" in sys.argv
    workflows_dir = REPO / "workflows"
    dirs = ([workflows_dir / a for a in args] if args
            else sorted(p.parent for p in workflows_dir.glob("*/workflow.json")))
    for d in dirs:
        apply_workflow(d, write=write, publish=publish)
