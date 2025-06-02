"""
transformations.py – drop‑in registry of AST transforms
=======================================================

This module is **auto‑imported** by *ast_helper.py* at start‑up.  Every class
decorated with `@register("NAME")` becomes a runnable transform:

    python ast_helper.py --transform NAME --path some/file.py [--preview]

Authoring checklist
-------------------
* **Set `change_id`** – a short, stable slug.  The helper appends
  `# @@<change_id>` at EOF so the patch is idempotent.
* **Implement at least one `visit_*` method** – or override `visit_Module` for
  whole‑file edits.
* **Always add `verify()`** – raise `VerificationError` when the mutation did
  *not* land as expected.  The helper rolls back automatically on failure.
* **Need a multi‑line snippet?**  Use
  `self.parse_snippet(" < code > ", ctx_node)` – it dedents, re‑indents to the
  current `col_offset` and returns an AST fragment ready to splice.
* **Need a persistent marker?**  Insert `self.keep_alive_marker()` – the
  unparser cannot drop a real assignment.

Tip: iterate with `--preview` until the diff is perfect.
"""

from ast import FunctionDef, Module, parse

from ast_helper import (  # type: ignore[reportMissingImports]
    BaseTransform,
    VerificationError,
    register,
)

# ──────────────────────────────────────────────────────────────────────
# Example transform 1 – simple function injection (legacy demo)
# ──────────────────────────────────────────────────────────────────────


@register("INSERT_PING")
class InsertPing(BaseTransform):
    """Append a `_ast_test_ping()` helper that always returns *"pong"*."""

    change_id = "insert_ping"
    probe_name, probe_expect = "_ast_test_ping", "pong"

    # ------------------------------------------------------------------
    # transform implementation
    # ------------------------------------------------------------------

    def visit_Module(self, node: Module):  # type: ignore[override]
        if any(isinstance(n, FunctionDef) and n.name == "_ast_test_ping" for n in node.body):
            return node  # idempotent — already patched

        fn = parse("def _ast_test_ping() -> str:\n" '    "Return static pong"\n' "    return 'pong'\n").body[0]
        node.body.append(fn)
        return node

    # ------------------------------------------------------------------
    # optional post‑patch verification
    # ------------------------------------------------------------------

    def verify(self, tree, _src_before):
        if not any(isinstance(n, FunctionDef) and n.name == "_ast_test_ping" for n in tree.body):
            raise VerificationError("ping missing after transform")


# ──────────────────────────────────────────────────────────────────────
# Example transform 2 – using parse_snippet + keep_alive_marker
# ──────────────────────────────────────────────────────────────────────


@register("DEMO_MARKER")
class DemoMarker(BaseTransform):
    """Drop a persistent marker assignment at the end of a module."""

    change_id = "demo_marker"

    def visit_Module(self, node: Module):  # type: ignore[override]
        # Already inserted?
        if any(
            hasattr(stmt, "targets") and any(getattr(t, "id", "") == "_demo_marker" for t in stmt.targets)
            for stmt in node.body
        ):
            return node

        # Insert a "live" marker so unparsing keeps it.
        node.body.append(self.keep_alive_marker("_demo_marker"))
        return node

    def verify(self, tree, _src_before):
        if not any(
            hasattr(stmt, "targets") and any(getattr(t, "id", "") == "_demo_marker" for t in stmt.targets)
            for stmt in tree.body
        ):
            raise VerificationError("demo marker not found after transform")
