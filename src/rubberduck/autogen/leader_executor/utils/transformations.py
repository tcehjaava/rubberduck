"""
transformations.py – drop-in registry of AST transforms
=======================================================

This module is **auto-imported** by `ast_helper.py` at start-up.
Every class decorated with `@register("NAME")` becomes a runnable
transform:

    python ast_helper.py --transform NAME --path file.py

Extra tips:
---------------------------------
• **Naming & deduping** – set `change_id` to a stable slug so the helper
  can skip patches that have already been applied.

• **Chaining transforms** – multiple classes may target the same file;
  they run one-after-the-other in the order you invoke them.

• **Debug flow** – use `--preview` to inspect the diff, `--check` to
  run `verify()` without writing, and `--verbose` (env VAR) for timing.
"""

from ast import FunctionDef, Module, parse

from ast_helper import (  # type: ignore[reportMissingImports]
    BaseTransform,
    VerificationError,
    register,
)


@register("INSERT_PING")
class InsertPing(BaseTransform):
    """Append a ``_ast_test_ping()`` function returning ``"pong"``."""

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
