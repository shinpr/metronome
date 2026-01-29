#!/usr/bin/env python3

"""
metronome: Detects shortcut-taking behavior and guides step-by-step execution.
Reads hook input from stdin, checks transcript for "efficiency" phrases.

Design note:
  This script runs as a Claude Code hook (PreToolUse). A hook that crashes or
  returns a non-zero exit code blocks the entire tool-use pipeline. Therefore
  the script treats all error paths — malformed JSON, missing files, encoding
  problems — as "allow" (silent exit 0). Keeping Claude's workflow running is
  the hook's primary responsibility; detection is best-effort.
"""

import json
import sys
import os

# Efficiency phrase stems in multiple languages.
# These are phrases Claude uses when attempting to take shortcuts.
#
# Substring matching is used intentionally instead of word-boundary matching.
# The goal is to catch shortcut-taking language broadly; false positives on
# negated forms like "inefficient" are an acceptable trade-off because the
# presence of such wording still signals efficiency-oriented thinking.
PATTERNS = [
    "efficien",    # English: efficient, efficiently, efficiency
    "効率",        # Japanese: 効率的, 効率化
    "高效",        # Chinese: highly efficient
    "效率",        # Chinese: efficiency
    "effizien",    # German: effizient, Effizienz
    "efficac",     # French: efficace, efficacement, efficacité
    "eficien",     # Spanish / Portuguese: eficiente, eficientemente, eficiencia
    "효율",        # Korean: 효율적으로, 효율화
    "эффектив",    # Russian: эффективно, эффективность
]

GUIDANCE = json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "Slow down.\n\n"
            "Read the current task, execute it, verify the result, "
            "then move to the next."
        ),
    }
})


def get_last_assistant_text(transcript_path):
    """Return text from the most recent assistant entry that contains text.

    Claude Code splits a single response into multiple JSONL entries
    (e.g. one for text, another for tool_use). The last entry at PreToolUse
    time is often a tool_use block with no text. This function skips such
    entries and finds the nearest assistant entry that has actual text.

    Stops searching when a non-assistant entry (e.g. user) is encountered,
    so only the current response is considered.
    """
    if not os.path.isfile(transcript_path):
        return ""

    lines = []
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-100:]
    except (OSError, UnicodeDecodeError):
        return ""

    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except (json.JSONDecodeError, TypeError):
            continue

    if not entries:
        return ""

    for entry in reversed(entries):
        if entry.get("type") != "assistant":
            break
        texts = []
        for block in entry.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    texts.append(text)
        if texts:
            return "\n".join(texts)

    return ""


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path:
        sys.exit(0)

    content = get_last_assistant_text(transcript_path)
    if not content:
        sys.exit(0)

    content_lower = content.lower()
    for pattern in PATTERNS:
        if pattern.lower() in content_lower:
            print(GUIDANCE)
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
