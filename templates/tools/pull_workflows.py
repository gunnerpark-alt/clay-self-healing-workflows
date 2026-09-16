#!/usr/bin/env python3
"""Pull Clay workflows into git-diffable files.

Layout per workflow:
  workflows/<slug>/workflow.json          graph: trigger, nodes (config), edges
  workflows/<slug>/nodes/<node>.prompt.md agent prompts, one file each
  workflows/<slug>/nodes/<node>.py        code bodies, one file each

Canonicalization rules (the whole point):
  - volatile/derived fields stripped (recentOutputPaths, positions, run stats, timestamps)
  - keys sorted, stable ordering of nodes (by id) and edges (by source, target)
  - prompt/code bodies externalized so diffs read as prose/code, not JSON strings

Run this twice with no live edits in between and the git diff should be empty.
If it isn't, something in this workspace's graph isn't canonicalizing cleanly —
fix that before relying on apply_workflows.py's diffs.
"""
import json, re, subprocess, sys, pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
VOLATILE_NODE_KEYS = {
    "recentOutputPaths", "position", "positions", "createdAt", "updatedAt",
    "lastRunAt", "agentClaygentId",  # claygent id is workspace-local, not portable
}

def sh(args):
    out = subprocess.run(["clay"] + args, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"clay {' '.join(args)}: {out.stderr[:400]}")
    return json.loads(out.stdout)

def slugify(name):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")

def node_slug(node):
    return slugify(node.get("name") or node["id"])

def normalize_platform_noise(n):
    """The read surface is unstable on a few details the write surface normalizes
    away. Canonicalize them so pull -> apply round-trips converge instead of
    diffing forever:
      - outputSchema.required comes back in arbitrary order -> sort
      - incomingEdges come back in arbitrary order -> sort by a stable key
      - inputSchema reference pins (sourceNodeId) nondeterministically gain/lose
        a redundant "type" -> drop it (the source node's schema is authoritative)
    """
    schema = n.get("outputSchema")
    if isinstance(schema, dict) and isinstance(schema.get("required"), list):
        schema["required"] = sorted(schema["required"])
    edges = n.get("incomingEdges")
    if isinstance(edges, list):
        n["incomingEdges"] = sorted(edges, key=lambda e: json.dumps(e, sort_keys=True))
    ischema = n.get("inputSchema")
    if isinstance(ischema, dict):
        for prop in (ischema.get("properties") or {}).values():
            if isinstance(prop, dict) and prop.get("sourceNodeId"):
                prop.pop("type", None)
    return n

def canonical_node(node, nodes_dir):
    n = {k: v for k, v in node.items() if k not in VOLATILE_NODE_KEYS and v is not None}
    normalize_platform_noise(n)
    slug = node_slug(node)
    prompt = n.pop("agentPrompt", None)
    if prompt:
        (nodes_dir / f"{slug}.prompt.md").write_text(prompt.rstrip() + "\n")
        n["agentPromptFile"] = f"nodes/{slug}.prompt.md"
    code = n.pop("code", None)
    if code:
        (nodes_dir / f"{slug}.py").write_text(code.rstrip() + "\n")
        n["codeFile"] = f"nodes/{slug}.py"
    return n

def pull_workflow(wf_id):
    graph = sh(["workflows", "graph", "get", wf_id, "--mode", "full"])
    summary = graph["summary"]
    slug = slugify(summary["workflowName"])
    wf_dir = REPO / "workflows" / slug
    nodes_dir = wf_dir / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    for old in nodes_dir.iterdir():
        old.unlink()

    nodes = sorted(graph.get("nodes") or [], key=lambda n: n["id"])
    doc = {
        "workflowId": summary["workflowId"],
        "workflowName": summary["workflowName"],
        "triggers": summary.get("triggers", []),
        "nodes": [canonical_node(n, nodes_dir) for n in nodes],
        "edges": sorted(
            summary.get("edges", []),
            key=lambda e: (e.get("sourceNodeId", ""), e.get("targetNodeId", "")),
        ),
    }
    (wf_dir / "workflow.json").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(f"pulled {summary['workflowName']} -> workflows/{slug} ({len(nodes)} nodes)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: pull_workflows.py <workflowId> [<workflowId> ...]")
        print("find ids with: clay workflows list")
        sys.exit(2)
    for wf_id in sys.argv[1:]:
        pull_workflow(wf_id)
