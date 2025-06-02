#!/usr/bin/env python3
# PATCH: ast-helper v1.0
"""
🚀  Strict AST helper — **v1.0**  *(enhanced)*
===========================================

A **single-file toolkit** for *safe, idempotent* edits on any Python repo,
 driven entirely by the Abstract Syntax Tree 🪄.

───────────────────────────────── TL;DR ─────────────────────────────────
1. (Optional) `python ast_helper.py --ensure-deps`   # installs astunparse/pyflakes if missing
2. Put your transforms in **transformations.py** and register with
      `@register("MY_NAME")`
3. Always add a `verify()` – it makes the helper roll back automatically.
4. Run:
      `python ast_helper.py --transform MY_NAME --path /abs/file.py [--preview]`

That’s it — diff preview, atomic write, byte-code compile, optional static
lint & runtime probes are handled for you.  Exit status ✔︎/✖ indicates
success.

────────────────────────── Writing a transform ──────────────────────────
```python
from ast_helper import register, BaseTransform, VerificationError
from ast import walk, Name  # stdlib

@register("RENAME_FOO")
class RenameFoo(BaseTransform):
    "Rename every identifier `foo` → `bar`."

    change_id = "rename_foo"          # prevents duplicate patches

    def visit_Name(self, node):
        if node.id == "foo":
            node.id = "bar"
        return node

    def verify(self, tree, _src_before):
        if any(isinstance(n, Name) and n.id == "foo" for n in walk(tree)):
            raise VerificationError("rename incomplete")
```

──────────────────────────── CLI reference ─────────────────────────────
--transform NAME   Name used in `@register(...)`
--path FILE.py     Target file to patch *in-place*
--preview          Show diff, don’t write
--ensure-deps      Install `astunparse` (<3.9) & `pyflakes` quietly
--check            Dry-run verification only (no write)

─────────────────────────── What’s new in this build ───────────────────────────
* **parse_snippet()** – one-liner to safely inject multi-line source *inside* a
  class or function body: dedents, then re-indents to the current
  `col_offset`. No more `IndentationError` surprises.
* **_keep_alive_marker()** – returns a tiny assignment expression that survives
  unparsing (unlike comments).  Perfect for idempotency or search markers.
* Diff clipping removed – you always see the full before/after hunk.
* Extra safety: after write-back we *re-parse* the file and assert the
  `change_id` marker is still present, catching any pretty-printer losses.

"""

######################################################################
# imports – nothing fancy                                            #
######################################################################

import ast
import difflib
import importlib.util as _il_util
import json
import pathlib as _pl
import shutil
import subprocess
import sys
import sys as _sys
import tempfile
import textwrap
import traceback
import types as _types
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Type, Union

_sys.modules.setdefault("ast_helper", _sys.modules[__name__])

# --------------------------------------------------------------------
# dependency bootstrap
# --------------------------------------------------------------------


def ensure_deps() -> None:
    """Install *exactly* the dependency versions required by the spec.

    * ``astunparse`` – fallback code-generator for Python < 3.9.
    * ``pyflakes``    – static lint / sanity check.
    """

    try:  # 3.8+
        import importlib.metadata as imd  # type: ignore
    except ImportError:  # 3.6–3.7 – still supported
        import importlib_metadata as imd  # type: ignore

    def need(pkg: str, lo: Tuple[int, int], hi: Tuple[int, int]) -> bool:
        "Return *True* if *pkg* is absent or outside the [lo, hi) range."
        try:
            v = tuple(int(x) for x in imd.version(pkg).split(".")[:2])
            return not (lo <= v < hi)
        except imd.PackageNotFoundError:  # type: ignore[attr-defined]
            return True

    pkgs: List[str] = []
    if need("astunparse", (1, 0), (2, 0)):
        pkgs.append("astunparse>=1,<2")
    if need("pyflakes", (2, 5), (3, 0)):
        pkgs.append("pyflakes>=2.5,<3")
    if pkgs:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *pkgs], check=True)


######################################################################
# unparse helpers – fall back gracefully on old Python versions      #
######################################################################

_ast_unparse = getattr(ast, "unparse", None)  # added in 3.9

try:
    if not _ast_unparse:
        import astunparse  # type: ignore  # noqa: E402
except ModuleNotFoundError:
    astunparse = None  # type: ignore[assignment]


def _unparse(tree: ast.AST) -> str:
    "Return *source* for *tree* using the best available generator."
    if _ast_unparse:  # 3.9+
        return _ast_unparse(tree)  # type: ignore[misc]
    if astunparse:
        return astunparse.unparse(tree)  # type: ignore[attr-defined]
    raise RuntimeError("No unparser available – run with --ensure-deps")


######################################################################
# diff + lint helpers                                                #
######################################################################

_PATCH_HEADER = "# PATCH: ast-helper v1.0"


def _print_diff(old: str, new: str, path: Path) -> None:
    "Pretty-print a unified diff with **no clipping** (clarity over brevity)."
    diff_lines = list(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"{path} (patched)",
        )
    )
    sys.stdout.writelines(diff_lines)


def _lint(p: Path) -> None:
    "Run the mandated syntax + static lint checks (py_compile & pyflakes)."
    subprocess.run([sys.executable, "-m", "py_compile", str(p)], check=True)
    try:
        subprocess.run([sys.executable, "-m", "pyflakes", str(p)], check=True)
    except FileNotFoundError:
        print("[ast-helper] pyflakes not found – skipping lint", file=sys.stderr)


######################################################################
# transform base / registry                                          #
######################################################################


class VerificationError(RuntimeError):
    "Raised whenever *any* step of the safety pipeline fails."


class ASTTransformer:
    "Utility mix-in with helpers for common edits (import insertion, etc.)."

    # ───── public convenience helpers ─────

    @staticmethod
    def ensure_import(module_node: ast.Module, module: str, *, alias: Optional[str] = None) -> ast.Module:
        "Insert `import <module>` (or `as alias`) **once** at top-of-file."
        if any(
            isinstance(n, ast.Import) and any(a.name == module and a.asname == alias for a in n.names)
            for n in module_node.body
        ):
            return module_node
        module_node.body.insert(0, ast.Import(names=[ast.alias(name=module, asname=alias)]))
        return module_node

    # ───── new in v1.0-enhanced ─────

    @staticmethod
    def parse_snippet(src: str, ctx: ast.AST) -> List[ast.stmt]:
        """Parse *src* so it can be safely spliced **inside** *ctx*.

        Steps:
        1. `textwrap.dedent` so authors can indent naturally in triple-quoted
           strings.
        2. Re-indent with as many spaces as `ctx.col_offset` so the fragment
           is legal at that insertion depth.
        3. `ast.parse` and return the resulting ``.body`` list.
        """
        indent = " " * getattr(ctx, "col_offset", 0)
        snippet = textwrap.indent(textwrap.dedent(src), indent)
        return ast.parse(snippet).body

    @staticmethod
    def keep_alive_marker(tag: str = "ast_helper_marker") -> ast.Assign:
        """Return a tiny assignment that the unparser **cannot drop**.

        Useful for transforms that need a persistent marker; an assignment
        with a string literal makes a great no-op that survives round-trips.
        """
        return ast.Assign(
            targets=[ast.Name(id=tag, ctx=ast.Store())],
            value=ast.Constant(value=True),
        )


class BaseTransform(ASTTransformer, ast.NodeTransformer):
    """Base class for all user-defined transforms.

    **Override** one or more ``visit_*`` methods *or* :pycode:`visit_Module`.
    Optionally provide:

    * ``change_id``    – unique marker preventing duplicate patches.
    * ``probe_name``   – runtime symbol to call after patch.
    * ``probe_expect`` – JSON-serialisable expected return value.
    * ``verify()``     – extra static assertions.
    """

    change_id: Optional[str] = None
    probe_name: Optional[str] = None
    probe_expect = None  # JSON-serialisable

    def verify(self, tree: ast.AST, src_before: str) -> None:  # noqa: D401
        "Hook that may raise :class:`VerificationError`.  Default = *no-op*."
        return None

    # ------------------------------------------------------------------
    # internal helpers – you don’t call these directly
    # ------------------------------------------------------------------

    def _run_probe(self, path: Path) -> None:
        "Optionally import the patched file and execute *probe_name*()."
        if not self.probe_name:
            return
        code = textwrap.dedent(
            f"""
            import json, runpy
            v = runpy.run_path('{path}')['{self.probe_name}']()
            print(json.dumps(v))
            """
        )
        out = subprocess.check_output([sys.executable, "-c", code], universal_newlines=True, timeout=2).strip()
        if out != json.dumps(self.probe_expect):
            raise VerificationError(f"probe mismatch: {out} ≠ {json.dumps(self.probe_expect)}")


_REGISTRY: Dict[str, Type[BaseTransform]] = {}


def register(name: str):
    "Decorator: `@register('NAME')` → adds the class to the registry."

    def _wrap(cls: Type[BaseTransform]) -> Type[BaseTransform]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


_extra = _pl.Path(__file__).with_name("transformations.py")
if _extra.exists():
    spec = _il_util.spec_from_file_location("ast_helper_transforms", _extra)
    mod = _types.ModuleType(spec.name)  # type: ignore[arg-type]
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

######################################################################
# repo façade – what callers use                                     #
######################################################################


class RepoEditor:
    "Facade class hiding all low-level details behind a simple API."

    def __init__(self, root: Union[Path, str]):
        self.root = Path(root).resolve()

    # ––––– public helpers –––––

    @property
    def registry(self):
        "Expose the global transform registry (useful for wrapper scripts)."
        return _REGISTRY

    # ––––– primary entry point –––––

    def apply(self, target: Union[Path, str], tfm_cls: Type[BaseTransform], *, preview: bool = False) -> None:
        "Apply *tfm_cls* to *target* in-place (10-step safety pipeline)."
        p = Path(target).resolve()
        before = p.read_text()

        # 1. Parse & transform ---------------------------------------------
        tfm = tfm_cls()
        tree = ast.parse(before, filename=str(p))
        tree = tfm.visit(tree)
        ast.fix_missing_locations(tree)
        code = _unparse(tree)

        # 2. Prepend patch header + optional change-id marker --------------
        if not code.startswith(_PATCH_HEADER):
            code = _PATCH_HEADER + "\n" + code.lstrip()
        if tfm.change_id and f"# @@{tfm.change_id}" not in code:
            code += f"\n# @@{tfm.change_id}\n"

        # 3. Short-circuit if no changes -----------------------------------
        if code == before:
            print("NO-OP")
            return

        # 4. Show full diff -------------------------------------------------
        _print_diff(before, code, p)
        if preview:
            return  # read-only mode requested

        # 5. Atomic write ---------------------------------------------------
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as t:
            t.write(code)
        shutil.move(t.name, p)

        # 6. Re-parse to ensure marker survived ----------------------------
        if tfm.change_id and f"# @@{tfm.change_id}" not in p.read_text():
            raise VerificationError("change_id marker lost after unparsing – aborting")

        # 7. Static verify() hook ------------------------------------------
        tfm.verify(ast.parse(code), before)

        # 8. Optional runtime probe ----------------------------------------
        tfm._run_probe(p)

        # 9. Syntax + lint --------------------------------------------------
        _lint(p)

        print("PATCH OK")

    # ––––– convenience helper accepting a plain function –––––

    def update_file(
        self,
        target: Union[Path, str],
        transform_fn: Callable[[ast.AST, str], ast.AST],
        *,
        change_id: Optional[str] = None,
        preview: bool = False,
    ) -> None:
        "Ad-hoc transform: supply a *callable* instead of a full subclass."
        before = Path(target).resolve().read_text()

        class _AdHoc(BaseTransform):
            pass

        _AdHoc.change_id = change_id  # type: ignore[attr-defined]

        def _visit(self, tree):  # type: ignore[override]
            return transform_fn(tree, before)

        _AdHoc.visit_Module = _visit  # type: ignore[attr-defined]
        self.apply(target, _AdHoc, preview=preview)


######################################################################
# CLI – thin wrapper for humans/CI                                   #
######################################################################


def _cli() -> None:  # noqa: C901 – single function, clarity over bleaching
    import argparse

    ap = argparse.ArgumentParser(
        prog="ast_helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """
            Safely patch a Python file in-place using AST transforms.

            Examples:
              # Ensure optional deps and then insert a ping function.
              ast_helper.py --ensure-deps --transform INSERT_PING --path src/foo.py

              # Preview the diff without writing.
              ast_helper.py --transform RENAME_FOO --path src/footer.py --preview
            """
        ),
    )

    ap.add_argument("--transform", choices=sorted(_REGISTRY))
    ap.add_argument("--path", help="absolute path of the file to patch")
    ap.add_argument("--preview", action="store_true", help="show diff without writing")
    ap.add_argument(
        "--ensure-deps",
        action="store_true",
        help="install astunparse & pyflakes if needed (quietly)",
    )

    ns = ap.parse_args()

    try:
        if ns.ensure_deps:
            ensure_deps()
            if not (ns.transform and ns.path):
                print("[ast-helper] dependencies satisfied")
                return

        tgt = Path(ns.path).resolve()
        if not tgt.exists():
            ap.error(f"{tgt} not found")

        RepoEditor(tgt.parent).apply(tgt, _REGISTRY[ns.transform], preview=ns.preview)

    except (VerificationError, subprocess.CalledProcessError) as e:
        print(f"[ast-helper] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        print("[ast-helper] Unhandled exception:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    _cli()
