from __future__ import annotations

import re
import uuid

from docker.models.containers import Container

from rubberduck.tools.container_manager import (
    run_script_in_container,
)

_PATCH_BEGIN = re.compile(r"^\s*\*\*\*\s*Begin Patch", re.MULTILINE)
_PATCH_END = re.compile(r"^\s*\*\*\*\s*End Patch", re.MULTILINE)


class PatchApplyError(RuntimeError):
    pass


def _extract_complete_patch(payload: str) -> str:
    m = _PATCH_BEGIN.search(payload)
    if not m:
        raise PatchApplyError("No *** Begin Patch found")

    n = _PATCH_END.search(payload, m.end())
    if not n:
        raise PatchApplyError("Unterminated *** Begin Patch block")

    return payload[m.start() : n.end()].lstrip()


def apply_patch_in_container(container: Container, patch_payload: str) -> None:
    patch_text = _extract_complete_patch(patch_payload)

    delim = f"PATCH_{uuid.uuid4().hex.upper()}"
    safe_patch = patch_text.replace(delim, f"{delim}_X")

    script = rf"""#!/bin/bash
set -euo pipefail

PATCH_FILE=$(mktemp /tmp/patch.XXXXXX)
cat >"$PATCH_FILE" <<'{delim}'
{safe_patch}
{delim}

if ! apply_patch <"$PATCH_FILE"; then
  echo "ERROR: apply_patch rejected the diff" >&2
  exit 1
fi

if command -v git >/dev/null 2>&1; then
  git add -u
fi

PYLIST=""
if command -v git >/dev/null 2>&1; then
  PYLIST=$(git diff --name-only --cached -- '*.py')
fi

if [ -n "$PYLIST" ]; then
  if ! python -m py_compile $PYLIST 2>/tmp/pycompile_error.log; then
    echo "SYNTAX_ERROR: Python compilation failed:" >&2
    cat /tmp/pycompile_error.log >&2
    exit 2
  fi
fi
"""
    exit_code, output = run_script_in_container(container, script)

    if exit_code == 0:
        return
    elif exit_code == 2:
        raise PatchApplyError("Patch applied but syntax errors detected:\n" + output)
    elif exit_code == 1:
        raise PatchApplyError("Patch application failed:\n" + output)
    else:
        raise PatchApplyError(f"Unexpected error (exit code {exit_code}):\n" + output)


def create_patch_reply(container: Container):
    def _handle(recipient, messages=None, **_):
        text = messages[-1].get("content", "")
        if "*** Begin Patch" not in text:
            return False, None

        try:
            apply_patch_in_container(container, text)
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
