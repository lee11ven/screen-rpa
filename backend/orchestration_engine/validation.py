from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .types import ALLOWED_LOOP_NODE_TYPES, ALLOWED_TOP_LEVEL_NODE_TYPES


def _err(path: str, message: str, node_id: str | None = None) -> dict[str, Any]:
    return {"path": path, "message": message, "node_id": node_id}


def validate_runtime(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    nodes = runtime.get("nodes")
    edges = runtime.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return [_err("", "runtime must include nodes/edges")]
    by_id = {str(n.get("id")): n for n in nodes if n.get("id")}
    starts = [n for n in nodes if n.get("type") == "start"]
    ends = [n for n in nodes if n.get("type") == "end"]
    if len(starts) != 1:
        errors.append(_err("nodes", "必须且仅有一个 start 节点"))
    if len(ends) < 1:
        errors.append(_err("nodes", "至少一个 end 节点"))
    for n in nodes:
        nid = str(n.get("id", ""))
        nt = str(n.get("type", ""))
        if nt not in ALLOWED_TOP_LEVEL_NODE_TYPES:
            errors.append(_err(f"nodes:{nid}.type", f"不支持的节点类型: {nt}", nid))
        if nt == "action":
            _validate_action(errors, n)
        if nt == "lowcode_function":
            _validate_lowcode(errors, n)
        if nt == "loop-container":
            _validate_loop_container(errors, n)
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        f = str(e.get("from", ""))
        t = str(e.get("to", ""))
        if f not in by_id or t not in by_id:
            errors.append(_err("edges", f"边引用未知节点: {f}->{t}", f))
            continue
        adj[f].append(t)
    if starts:
        seen: set[str] = set()
        queue: deque[str] = deque([str(starts[0]["id"])])
        while queue:
            cur = queue.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            for nxt in adj.get(cur, []):
                queue.append(nxt)
        for n in nodes:
            nid = str(n.get("id"))
            if nid not in seen:
                errors.append(_err("nodes", f"不可达节点: {nid}", nid))
    return errors


def _validate_lowcode(errors: list[dict[str, Any]], node: dict[str, Any]) -> None:
    nid = str(node.get("id", ""))
    cfg = node.get("config") or {}
    code_body = str(cfg.get("code_body", ""))
    if not code_body.strip():
        errors.append(_err(f"nodes:{nid}.config.code_body", "lowcode_function 必须填写 code_body", nid))
        return
    wrapped = "def run(context, services):\n" + "\n".join(f"    {line}" for line in code_body.splitlines())
    try:
        compile(wrapped, "<lowcode>", "exec")
    except Exception as exc:  # noqa: BLE001
        errors.append(_err(f"nodes:{nid}.config.code_body", f"CompileError: {exc}", nid))


def _validate_action(errors: list[dict[str, Any]], node: dict[str, Any]) -> None:
    nid = str(node.get("id", ""))
    cfg = node.get("config") or {}
    action_key = str(cfg.get("action_key", "")).strip()
    if not action_key:
        errors.append(_err(f"nodes:{nid}.config.action_key", "action 节点必须配置 action_key", nid))
    if not isinstance(cfg.get("params", {}), dict):
        errors.append(_err(f"nodes:{nid}.config.params", "action params 必须是对象", nid))
    for key in ("timeout_ms", "poll_interval_ms", "retry_times", "retry_interval_ms", "post_delay_ms", "jitter_ms"):
        if key in cfg:
            try:
                value = int(cfg.get(key, 0))
            except Exception:  # noqa: BLE001
                errors.append(_err(f"nodes:{nid}.config.{key}", f"{key} 必须是非负整数", nid))
                continue
            if value < 0:
                errors.append(_err(f"nodes:{nid}.config.{key}", f"{key} 必须是非负整数", nid))
    node_on_error = str(node.get("on_error", "fail")).strip()
    if node_on_error and node_on_error not in ("fail", "retry", "skip", "to_node", "continue"):
        errors.append(_err(f"nodes:{nid}.on_error", f"不支持的 on_error: {node_on_error}", nid))


def _validate_loop_container(errors: list[dict[str, Any]], node: dict[str, Any]) -> None:
    nid = str(node.get("id", ""))
    cfg = node.get("config") or {}
    sub_graph = cfg.get("subGraph")
    if not isinstance(sub_graph, dict):
        errors.append(_err(f"nodes:{nid}.config.subGraph", "subGraph 必须是对象", nid))
        return
    sub_nodes = sub_graph.get("nodes")
    sub_edges = sub_graph.get("edges")
    if not isinstance(sub_nodes, list) or not isinstance(sub_edges, list):
        errors.append(_err(f"nodes:{nid}.config.subGraph", "subGraph 必须包含 nodes/edges 数组", nid))
        return
    starts = [n for n in sub_nodes if n.get("type") == "loop_start"]
    if len(starts) != 1:
        errors.append(_err(f"nodes:{nid}.config.subGraph.nodes", "loop 子图必须且仅有一个 loop_start", nid))
    if not any(n.get("type") in ("continue", "break") for n in sub_nodes):
        errors.append(_err(f"nodes:{nid}.config.subGraph.nodes", "loop 子图至少需要 continue 或 break", nid))
    by_id = {str(n.get("id")): n for n in sub_nodes if n.get("id")}
    adj: dict[str, list[str]] = defaultdict(list)
    for n in sub_nodes:
        sid = str(n.get("id", ""))
        nt = str(n.get("type", ""))
        if nt not in ALLOWED_LOOP_NODE_TYPES:
            errors.append(_err(f"nodes:{nid}.config.subGraph.nodes:{sid}.type", f"loop 子图不支持节点类型: {nt}", sid))
    for e in sub_edges:
        f = str(e.get("from", ""))
        t = str(e.get("to", ""))
        if f not in by_id or t not in by_id:
            errors.append(_err(f"nodes:{nid}.config.subGraph.edges", f"子图边引用未知节点: {f}->{t}", nid))
            continue
        adj[f].append(t)
    if len(starts) == 1:
        queue: deque[str] = deque([str(starts[0].get("id"))])
        seen: set[str] = set()
        while queue:
            cur = queue.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            curr_type = str((by_id.get(cur) or {}).get("type", ""))
            if curr_type not in ("if", "continue", "break") and len(adj.get(cur, [])) == 0:
                errors.append(_err(f"nodes:{nid}.config.subGraph", f"存在自然结束路径: {cur}", cur))
            for nxt in adj.get(cur, []):
                queue.append(nxt)
