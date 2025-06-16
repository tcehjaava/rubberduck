from __future__ import annotations

import concurrent
import re
import shlex
from typing import Iterable, List, Tuple

_PARAM_RE = re.compile(r"^(?P<base>[^\[]+)\[.*\]$")


def _can_collect(container, node: str, workdir: str) -> bool:
    exit_code, _ = container.exec_run(
        ["bash", "-lc", f"pytest --collect-only -q {shlex.quote(node)}"],
        user="root",
        workdir=workdir,
    )
    return exit_code == 0


def _first_pass(container, nodes: Iterable[str], workdir: str) -> List[str]:
    kept = []
    with concurrent.futures.ThreadPoolExecutor() as pool:
        for node, ok in zip(nodes, pool.map(lambda n: _can_collect(container, n, workdir), nodes)):
            if ok:
                kept.append(node)
            else:
                m = _PARAM_RE.match(node)
                if m:
                    base = m.group("base")
                    if _can_collect(container, base, workdir):
                        kept.append(base)
    return kept


def _dedup(nodes: Iterable[str]) -> List[str]:
    kept_set = set(nodes)
    out = []
    for n in nodes:
        m = _PARAM_RE.match(n)
        if m and m.group("base") in kept_set and m.group("base") != n:
            continue
        if n not in out:
            out.append(n)
    return out


def prune_env(
    container, fail_nodes: Iterable[str], pass_nodes: Iterable[str], workdir: str
) -> Tuple[List[str], List[str]]:
    workdir = str(workdir)
    fail_final = sorted(_dedup(_first_pass(container, fail_nodes, workdir)))
    pass_final = sorted(_dedup(_first_pass(container, pass_nodes, workdir)))
    return fail_final, pass_final
