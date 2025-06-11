from __future__ import annotations

import re
import shlex
import textwrap
import uuid
from typing import List

from autogen.coding import CodeBlock, DockerCommandLineCodeExecutor

_PATCH_BEGIN = re.compile(r"^\s*\*\*\*\s*Begin Patch", re.MULTILINE)
_PATCH_END = re.compile(r"^\s*\*\*\*\s*End Patch", re.MULTILINE)

_PATCH_HEADER_RE = re.compile(r"^\s*---\s+(?P<fname>.+)")


class PatchApplyError(RuntimeError):
    pass


def _extract_blocks(payload: str) -> List[str]:
    blocks: List[str] = []
    for m in _PATCH_BEGIN.finditer(payload):
        n = _PATCH_END.search(payload, m.end())
        if not n:
            raise PatchApplyError("Unterminated *** Begin Patch block")
        content = payload[m.end() : n.start()].strip()
        if content:
            blocks.append(content)
    if not blocks:
        raise PatchApplyError("No valid patch content found")
    return blocks


def _needs_strip_p1(patch_text: str) -> bool:
    for raw_line in patch_text.splitlines():
        match = _PATCH_HEADER_RE.match(raw_line.expandtabs())
        if match:
            return match.group("fname").lstrip().startswith(("a/", "b/"))
    return False


def apply_patch_via_executor(
    executor: DockerCommandLineCodeExecutor,
    patch_payload: str,
    workspace_mount: str = "/workspace",
) -> None:
    blocks = _extract_blocks(patch_payload)
    patch_text = "\n".join(textwrap.dedent(b).lstrip("\n") for b in blocks)

    delim = f"PATCH_{uuid.uuid4().hex.upper()}"
    safe_patch = patch_text.replace(delim, f"{delim}_X")
    strip_opt = "-p1" if _needs_strip_p1(patch_text) else "-p0"
    ws = shlex.quote(workspace_mount)

    script = rf"""#!/bin/bash
set -euo pipefail

if ! command -v git >/dev/null 2>&1 && ! command -v patch >/dev/null 2>&1; then
  echo "ERROR: neither git nor patch is installed" >&2; exit 1;
fi

cd {ws}

PATCH_FILE=$(mktemp /tmp/patch.XXXXXX)
cat > "$PATCH_FILE" <<'{delim}'
{safe_patch}
{delim}

cleanup() {{ rm -f "$PATCH_FILE"; }}
trap cleanup EXIT

if command -v git >/dev/null 2>&1 && git apply --check "$PATCH_FILE" >/dev/null 2>&1; then
  git apply --index --whitespace=nowarn "$PATCH_FILE"
elif command -v patch >/dev/null 2>&1 && patch {strip_opt} --dry-run --batch < "$PATCH_FILE"; then
  patch {strip_opt} --batch --forward < "$PATCH_FILE"
else
  echo "ERROR: patch rejected by both git and patch" >&2; exit 1
fi

if command -v git >/dev/null 2>&1; then
  PYLIST=$(git diff --name-only --cached | grep -E '\\.py$' || true)
else
  PYLIST=$(grep -E '^\+\+\+ ' "$PATCH_FILE" | awk '{{print $2}}' | sed 's|^[ab]/||' | grep -E '\\.py$' || true)
fi

if [ -n "$PYLIST" ]; then
  echo "Running py_compile on: $PYLIST"
  python -m py_compile $PYLIST || {{ echo "PYCOMPILE_FAILED" >&2; exit 2; }}
fi

echo "Patch + syntax check OK"
exit 0
"""

    result = executor.execute_code_blocks([CodeBlock(language="bash", code=script)])

    if result.exit_code == 0:
        return
    elif result.exit_code == 2:
        raise PatchApplyError("Patch applied but syntax errors detected:\n" + result.output)
    else:
        raise PatchApplyError(result.output)


def create_patch_reply(executor: DockerCommandLineCodeExecutor):
    def _handle(recipient, messages=None, **_):
        text = messages[-1].get("content", "")
        if "*** Begin Patch" not in text:
            return False, None

        try:
            apply_patch_via_executor(executor, text)
            recipient._last_patch_status = "✅ Patch applied & py_compile succeeded."
        except PatchApplyError as err:
            recipient._last_patch_status = f"❌ {err}"
        return False, None

    return _handle


def prepend_patch_status(sender, message, *_, **kwargs):
    status = getattr(sender, "_last_patch_status", None)
    if not status:
        return message
    if isinstance(message, str):
        new_msg = f"{status}\n\n{message}"
    else:
        new_msg = message.copy()
        new_msg["content"] = f"{status}\n\n{message.get('content', '')}"
    sender._last_patch_status = None
    return new_msg
