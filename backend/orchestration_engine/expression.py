from __future__ import annotations

import ast
import re
from typing import Any, Mapping

_VAR = re.compile(r"\$\{([^}]+)\}")
_SIMPLE_VAR = re.compile(r"^(input|ctx|loop)\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\.\d+)*$")


def _resolve_path(root: Any, path: str) -> Any:
    cur: Any = root
    for part in path.split("."):
        if isinstance(cur, Mapping):
            cur = cur.get(part)
        elif isinstance(cur, (list, tuple)):
            cur = cur[int(part)]
        else:
            return None
    return cur


def _to_literal_fragment(v: Any) -> str:
    if v is None:
        return "None"
    if isinstance(v, bool):
        return "True" if v else "False"
    return repr(v)


def substitute_vars(expr: str, input_obj: Mapping[str, Any], ctx: Mapping[str, Any], loop: Mapping[str, Any] | None) -> str:
    loop = loop or {}

    def replace_one(inner: str) -> str:
        if inner.startswith("input."):
            return _to_literal_fragment(_resolve_path(dict(input_obj), inner[6:]))
        if inner.startswith("ctx."):
            return _to_literal_fragment(_resolve_path(dict(ctx), inner[4:]))
        if inner.startswith("loop."):
            return _to_literal_fragment(_resolve_path(dict(loop), inner[5:]))
        raise ValueError(f"unsupported template: ${{{inner}}}")

    simple_var = expr.strip()
    if _SIMPLE_VAR.fullmatch(simple_var):
        return replace_one(simple_var)

    out: list[str] = []
    pos = 0
    for m in _VAR.finditer(expr):
        out.append(expr[pos : m.start()])
        out.append(replace_one(m.group(1).strip()))
        pos = m.end()
    out.append(expr[pos:])
    return "".join(out)


def _eval_ast(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not bool(_eval_ast(node.operand))
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        return left / right
    if isinstance(node, ast.Compare):
        left = _eval_ast(node.left)
        cur = left
        for op, comp in zip(node.ops, node.comparators, strict=True):
            right = _eval_ast(comp)
            if type(op) is ast.Eq:
                ok = cur == right
            elif type(op) is ast.NotEq:
                ok = cur != right
            elif type(op) is ast.Gt:
                ok = cur > right
            elif type(op) is ast.GtE:
                ok = cur >= right
            elif type(op) is ast.Lt:
                ok = cur < right
            elif type(op) is ast.LtE:
                ok = cur <= right
            else:
                raise ValueError("unsupported compare op")
            if not ok:
                return False
            cur = right
        return True
    if isinstance(node, ast.BoolOp):
        values = [_eval_ast(v) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in values)
        if isinstance(node.op, ast.Or):
            return any(bool(v) for v in values)
    raise ValueError("unsupported expression ast")


def evaluate_bool_expression(expr: str, input_obj: Mapping[str, Any], ctx: Mapping[str, Any], loop: Mapping[str, Any] | None) -> bool:
    s = substitute_vars(expr, input_obj, ctx, loop).strip()
    tree = ast.parse(s, mode="eval")
    return bool(_eval_ast(tree))
