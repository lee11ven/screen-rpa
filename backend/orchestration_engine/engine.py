from __future__ import annotations

import ast
import json
import logging
import random
import time
from time import monotonic
from typing import Any, Callable

from .errors import (
    LoopBreakSignal,
    LoopContinueSignal,
    LowcodeCompileError,
    LowcodeProtocolError,
    LowcodeRuntimeError,
    LowcodeTimeoutError,
    RunCancelledError,
)
from .expression import evaluate_bool_expression, substitute_vars
from .lowcode_config import LOWCODE_BUILTINS
from .ports import ActionExecutorPort, LowcodeRuntimePort, WorkflowDefinitionPort
from .types import ExecutorHooks

logger = logging.getLogger(__name__)


class RuntimeExecutor:
    def __init__(
        self,
        runtime: dict[str, Any],
        input_obj: dict[str, Any],
        hooks: ExecutorHooks | None,
        definition_port: WorkflowDefinitionPort,
        action_port: ActionExecutorPort | None,
        lowcode_runtime: LowcodeRuntimePort,
        services: dict[str, Any] | None = None,
        initial_ctx: dict[str, Any] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> None:
        self.runtime = runtime
        self.input_obj = input_obj
        self.hooks = hooks or ExecutorHooks()
        self.definition_port = definition_port
        self.action_port = action_port
        self.lowcode_runtime = lowcode_runtime
        self.services = services or {}
        self.ctx = dict(initial_ctx or {})
        self.cancel_requested = cancel_requested
        self.node_results: dict[str, Any] = {}
        self.settings = runtime.get("settings") or {}
        self.nodes: dict[str, Any] = {n["id"]: n for n in runtime.get("nodes", [])}
        self.edges: list[dict[str, Any]] = list(runtime.get("edges", []))
        self._loop_stack: list[dict[str, Any]] = []

    @property
    def _loop_env(self) -> dict[str, Any] | None:
        return self._loop_stack[-1] if self._loop_stack else None

    def _log(self, level: str, message: str, node_id: str | None = None, **ctx: Any) -> None:
        if self.hooks.on_log:
            self.hooks.on_log(level, node_id, message, dict(ctx))

    def _out_edges(self, from_id: str) -> list[tuple[str, str | None, dict[str, Any] | None]]:
        outs: list[tuple[str, str | None, dict[str, Any] | None]] = []
        for e in self.edges:
            if e.get("from") != from_id:
                continue
            cond = e.get("condition")
            if not isinstance(cond, dict):
                cond = None
            outs.append((str(e.get("to")), e.get("label"), cond))
        return outs

    def run(self) -> str:
        starts = [n["id"] for n in self.runtime.get("nodes", []) if n.get("type") == "start"]
        if len(starts) != 1:
            raise RuntimeError("invalid workflow: start")
        self._execute_block(starts[0], stop_at=None)
        return "SUCCESS"

    def _execute_block(self, cur: str | None, stop_at: str | None) -> None:
        while cur is not None and cur != stop_at:
            self._check_cancelled()
            cur = self._execute_one(cur)

    def _check_cancelled(self) -> None:
        checker = self.cancel_requested
        if checker is None:
            return
        if checker():
            raise RunCancelledError("run cancelled")

    def _execute_one(self, cur: str) -> str | None:
        self._check_cancelled()
        node = self.nodes[cur]
        node_id = str(node["id"])
        node_type = str(node["type"])
        if self.hooks.on_node_start:
            self.hooks.on_node_start(node_id)
        try:
            next_override = self._execute_node_body(node)
            if self.hooks.on_node_finish:
                self.hooks.on_node_finish(node_id, "SUCCESS", None)
            if node_type in ("if",):
                return next_override
            outs = self._out_edges(node_id)
            if not outs:
                return None
            if len(outs) > 1:
                raise RuntimeError(f"ambiguous outgoing edges from {node_id}")
            return outs[0][0]
        except (LoopContinueSignal, LoopBreakSignal):
            if self.hooks.on_node_finish:
                self.hooks.on_node_finish(node_id, "SUCCESS", None)
            raise
        except Exception as ex:  # noqa: BLE001
            if self.hooks.on_node_finish:
                self.hooks.on_node_finish(node_id, "FAILED", str(ex))
            raise

    def _execute_node_body(self, node: dict[str, Any]) -> str | None:
        nt = str(node.get("type"))
        if nt in ("start", "end", "loop_start"):
            return None
        if nt == "action":
            self._exec_action(node)
            return None
        if nt == "if":
            return self._next_if(node)
        if nt == "wait":
            self._exec_wait(node)
            return None
        if nt == "subflow":
            self._exec_subflow(node)
            return None
        if nt == "lowcode_function":
            self._exec_lowcode_function(node)
            return None
        if nt == "continue":
            sleep_ms = int((node.get("config") or {}).get("sleep_ms", 0))
            if sleep_ms > 0:
                time.sleep(sleep_ms / 1000.0)
            raise LoopContinueSignal()
        if nt == "break":
            raise LoopBreakSignal()
        if nt == "loop-container":
            self._exec_loop(node)
            return None
        raise RuntimeError(f"unsupported node type: {nt}")

    def _exec_loop(self, node: dict[str, Any]) -> None:
        cfg = node.get("config") or {}
        sub_graph = cfg.get("subGraph") or {}
        sub_nodes = sub_graph.get("nodes")
        sub_edges = sub_graph.get("edges")
        if not isinstance(sub_nodes, list) or not isinstance(sub_edges, list):
            raise RuntimeError("loop-container invalid subGraph")
        starts = [n for n in sub_nodes if n.get("type") == "loop_start"]
        if len(starts) != 1:
            raise RuntimeError("loop-container requires exactly one loop_start")
        old_nodes = self.nodes
        old_edges = self.edges
        loop_id = str(cfg.get("loopId", node["id"]))
        self.nodes = {n["id"]: n for n in sub_nodes}
        self.edges = list(sub_edges)
        try:
            idx = 0
            while True:
                self._loop_stack.append({"id": loop_id, "index": idx, "iteration": idx + 1})
                try:
                    self._execute_block(str(starts[0]["id"]), stop_at=None)
                except LoopContinueSignal:
                    idx += 1
                    continue
                except LoopBreakSignal:
                    break
                else:
                    raise RuntimeError("loop 子图存在自然结束路径（未命中 continue/break）")
                finally:
                    self._loop_stack.pop()
        finally:
            self.nodes = old_nodes
            self.edges = old_edges

    def _next_if(self, node: dict[str, Any]) -> str | None:
        node_id = str(node["id"])
        try:
            for to, lbl, condition in self._out_edges(node_id):
                if self._eval_if_edge_condition(lbl, condition):
                    return to
            raise RuntimeError(f"if 无匹配分支: {node_id}")
        except Exception as ex:  # noqa: BLE001
            self._log("error", "if 分支匹配失败，结束当前执行链", node_id, error=str(ex))
            logger.exception("if 分支匹配失败，结束当前执行链: node_id=%s", node_id)
            return None

    def _eval_if_edge_condition(self, label: Any, condition: dict[str, Any] | None) -> bool:
        if isinstance(condition, dict):
            ok, _ = self._check_condition(condition, None)
            return ok
        expr = "" if label is None else str(label).strip()
        if not expr:
            return False
        return evaluate_bool_expression(expr, self.input_obj, self.ctx, self._loop_env)

    def _exec_wait(self, node: dict[str, Any]) -> None:
        cfg = node.get("config") or {}
        cond = cfg.get("condition")
        timeout_ms = int(cfg.get("timeout_ms", 5000))
        poll_interval_ms = int(cfg.get("poll_interval_ms", 150))
        started = monotonic()
        baseline: str | None = None
        while int((monotonic() - started) * 1000) <= timeout_ms:
            self._check_cancelled()
            ok, baseline = self._check_condition(cond, baseline)
            if ok:
                self.node_results[str(node["id"])] = {"ok": True}
                return
            time.sleep(max(0.02, poll_interval_ms / 1000.0))
        raise RuntimeError("wait condition timeout")

    def _check_condition(self, condition: Any, baseline_clipboard: str | None) -> tuple[bool, str | None]:
        if not isinstance(condition, dict):
            return False, baseline_clipboard
        kind = str(condition.get("kind", "none"))
        params = condition.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        if kind == "none":
            return True, baseline_clipboard
        if kind == "expression":
            expr = str(params.get("expr", "false"))
            return evaluate_bool_expression(expr, self.input_obj, self.ctx, self._loop_env), baseline_clipboard
        if self.action_port is None:
            raise RuntimeError(f"condition {kind} requires action port")
        if kind in ("image_exists", "image_not_exists", "sub_image_exists", "sub_image_not_exists"):
            try:
                out = self.action_port.execute(
                    "system.image_locate_center",
                    {
                        "template_path": str(params.get("template_path", "")).strip(),
                        "threshold": float(params.get("threshold", 0.85)),
                        "page_path": params.get("page_path", ""),
                    },
                )
                exists = bool((out.get("data") or {}).get("x") is not None)
            except Exception:  # noqa: BLE001
                exists = False
            return (exists if "not" not in kind else (not exists)), baseline_clipboard
        if kind == "window_active":
            try:
                out = self.action_port.execute(
                    "system.window_find",
                    {"title": params.get("title", ""), "process_name": params.get("process_name", "")},
                )
                data = out.get("data") or {}
                return bool(data.get("found") or data.get("hwnd")), baseline_clipboard
            except Exception:  # noqa: BLE001
                return False, baseline_clipboard
        if kind == "clipboard_changed":
            try:
                out = self.action_port.execute("system.clipboard_get_text", {})
                now_text = str((out.get("data") or {}).get("text", ""))
            except Exception:  # noqa: BLE001
                now_text = ""
            expected = str(params.get("expected_text", "")).strip()
            if expected:
                return now_text == expected, baseline_clipboard
            if baseline_clipboard is None:
                return False, now_text
            return now_text != baseline_clipboard, baseline_clipboard
        return False, baseline_clipboard

    def _render_action_params(self, value: Any) -> Any:
        if isinstance(value, str):
            rendered = substitute_vars(value, self.input_obj, self.ctx, self._loop_env)
            for parser in (json.loads, ast.literal_eval):
                try:
                    return parser(rendered)
                except Exception:  # noqa: BLE001
                    pass
            return rendered
        if isinstance(value, dict):
            return {str(k): self._render_action_params(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._render_action_params(item) for item in value]
        return value

    def _wait_action_success(self, condition: Any, timeout_ms: int, poll_interval_ms: int) -> bool:
        baseline: str | None = None
        started = monotonic()
        while True:
            self._check_cancelled()
            ok, baseline = self._check_condition(condition, baseline)
            if ok:
                return True
            if timeout_ms <= 0:
                return False
            if int((monotonic() - started) * 1000) > timeout_ms:
                return False
            time.sleep(max(0.02, poll_interval_ms / 1000.0))

    def _exec_action(self, node: dict[str, Any]) -> None:
        if self.action_port is None:
            raise RuntimeError("action node requires action port")
        cfg = node.get("config") or {}
        action_key = str(cfg.get("action_key", "")).strip()
        if not action_key:
            raise RuntimeError("action node requires action_key")
        params_raw = cfg.get("params")
        params = self._render_action_params(params_raw if isinstance(params_raw, dict) else {})
        timeout_ms = max(0, int(cfg.get("timeout_ms", int(self.settings.get("default_timeout_sec", 3)) * 1000)))
        poll_interval_ms = max(20, int(cfg.get("poll_interval_ms", 150)))
        retry_times = max(0, int(cfg.get("retry_times", 0)))
        retry_interval_ms = max(0, int(cfg.get("retry_interval_ms", 0)))
        success_condition = cfg.get("success_condition") or {"kind": "none", "params": {}}
        on_error = str(node.get("on_error", "fail")).strip().lower() or "fail"
        if on_error == "retry" and "retry_times" not in cfg:
            retry_times = max(retry_times, int(self.settings.get("max_retries", 0)))
        attempts = retry_times + 1
        last_error: Exception | None = None
        last_result: dict[str, Any] | None = None
        for idx in range(attempts):
            self._check_cancelled()
            self._log(
                "info",
                "action attempt started",
                str(node["id"]),
                action_key=action_key,
                attempt=idx + 1,
                max_attempts=attempts,
                params=params,
            )
            try:
                result = self.action_port.execute(action_key, params)
                last_result = result
                self._log(
                    "info",
                    "action attempt executed",
                    str(node["id"]),
                    action_key=action_key,
                    attempt=idx + 1,
                    result=result,
                )
                if self._wait_action_success(success_condition, timeout_ms, poll_interval_ms):
                    self.node_results[str(node["id"])] = result
                    self._log("info", "action succeeded", str(node["id"]), action_key=action_key, attempt=idx + 1)
                    break
                last_error = RuntimeError(f"action success condition not met within timeout: {timeout_ms}ms")
            except Exception as ex:  # noqa: BLE001
                last_error = ex
            if idx < attempts - 1:
                self._check_cancelled()
                if retry_interval_ms > 0:
                    time.sleep(retry_interval_ms / 1000.0)
                self._log("warning", "action attempt failed, retrying", str(node["id"]), attempt=idx + 1, max_attempts=attempts, error=str(last_error))
        else:
            self._log("error", "action failed", str(node["id"]), action_key=action_key, error=str(last_error or "action failed"))
            if on_error in ("skip", "continue"):
                self.node_results[str(node["id"])] = {
                    "success": False,
                    "code": "SKIPPED",
                    "message": str(last_error or "action failed"),
                    "data": (last_result or {}).get("data", {}),
                }
                return
            if on_error == "to_node":
                raise RuntimeError("on_error=to_node is not supported yet")
            raise last_error or RuntimeError("action failed")
        post_delay_ms = max(0, int(cfg.get("post_delay_ms", 0)))
        jitter_ms = max(0, int(cfg.get("jitter_ms", 0)))
        extra_jitter_ms = random.randint(0, jitter_ms) if jitter_ms > 0 else 0
        sleep_ms = post_delay_ms + extra_jitter_ms
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000.0)

    def _exec_subflow(self, node: dict[str, Any]) -> None:
        cfg = node.get("config") or {}
        wid = str(cfg.get("workflow_id", "")).strip()
        if not wid:
            raise RuntimeError("subflow requires workflow_id")
        child_ver = cfg.get("workflow_version")
        runtime = self.definition_port.load_published_runtime(wid, int(child_ver) if child_ver is not None else None)
        mapping = cfg.get("input_mapping") or {}
        child_input: dict[str, Any] = {}
        if isinstance(mapping, dict):
            for k, templ in mapping.items():
                if not isinstance(templ, str):
                    continue
                raw = substitute_vars(templ, self.input_obj, self.ctx, self._loop_env).strip()
                try:
                    child_input[k] = json.loads(raw)
                except json.JSONDecodeError:
                    child_input[k] = raw.strip('"')
        sub = RuntimeExecutor(
            runtime=runtime,
            input_obj=child_input,
            hooks=self.hooks,
            definition_port=self.definition_port,
            action_port=self.action_port,
            lowcode_runtime=self.lowcode_runtime,
            services=self.services,
            initial_ctx=self.ctx,
        )
        sub.run()

    def _normalize_lowcode_result(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            out = dict(value)
        else:
            out = {"data": value}
        out.setdefault("ok", True)
        out.setdefault("code", "OK" if bool(out.get("ok")) else "ERR")
        out.setdefault("message", "OK" if bool(out.get("ok")) else "ERROR")
        out.setdefault("data", None)
        return out

    def _exec_lowcode_function(self, node: dict[str, Any]) -> None:
        cfg = node.get("config") or {}
        code_body = str(cfg.get("code_body", "")).strip()
        if not code_body:
            raise LowcodeProtocolError("lowcode code_body is empty")
        timeout_ms = int(cfg.get("timeout_ms", 3000))
        try:
            result = self.lowcode_runtime.run(code_body, self.ctx, self.services, timeout_ms)
        except (LowcodeCompileError, LowcodeRuntimeError, LowcodeTimeoutError, LowcodeProtocolError):
            raise
        self.node_results[str(node["id"])] = self._normalize_lowcode_result(result)


class DefaultLowcodeRuntime:
    def run(self, code_body: str, ctx: dict[str, Any], services: dict[str, Any], timeout_ms: int) -> Any:
        wrapped_source = "def run(ctx, services):\n" + "\n".join(f"    {line}" for line in code_body.splitlines())
        global_ns = {"__builtins__": dict(LOWCODE_BUILTINS)}
        local_ns: dict[str, Any] = {}
        try:
            exec(compile(wrapped_source, "<lowcode>", "exec"), global_ns, local_ns)
        except Exception as exc:  # noqa: BLE001
            raise LowcodeCompileError(str(exc)) from exc
        fn = local_ns.get("run") or global_ns.get("run")
        if not callable(fn):
            raise LowcodeCompileError("compiled lowcode function run not found")
        started = monotonic()
        try:
            result = fn(ctx, services)
        except Exception as exc:  # noqa: BLE001
            raise LowcodeRuntimeError(str(exc)) from exc
        if timeout_ms > 0 and int((monotonic() - started) * 1000) > timeout_ms:
            raise LowcodeTimeoutError(f"lowcode timeout after {timeout_ms}ms")
        if result is None:
            raise LowcodeProtocolError("lowcode return value cannot be None")
        return result
