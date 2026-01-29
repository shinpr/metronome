#!/usr/bin/env python3

"""Tests for metronome check-efficiency script."""

import json
import os
import subprocess
import tempfile
import unittest

SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "metronome",
    "scripts",
    "check-efficiency.py",
)


def make_assistant_entry(text):
    """Create an assistant transcript entry."""
    return json.dumps({
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": text}]
        },
    })


def make_tool_use_entry():
    """Create an assistant transcript entry with only a tool_use block."""
    return json.dumps({
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "id": "test", "name": "Bash",
                         "input": {"command": "echo hello"}}]
        },
    })


def make_user_entry(text):
    """Create a user transcript entry."""
    return json.dumps({"type": "user", "message": {"content": text}})


def run_hook(transcript_path):
    """Run the hook script with a given transcript path."""
    hook_input = json.dumps({
        "session_id": "test-session",
        "transcript_path": transcript_path,
        "cwd": "/tmp",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo hello"},
    })
    result = subprocess.run(
        ["python3", SCRIPT_PATH],
        input=hook_input,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result


def write_transcript(lines):
    """Write transcript lines to a temp file, return path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    f.write("\n".join(lines) + "\n")
    f.close()
    return f.name


def assert_allowed(test, result):
    """Assert the hook allowed execution (no output, exit 0)."""
    test.assertEqual(result.returncode, 0)
    test.assertEqual(result.stdout.strip(), "")


def assert_blocked(test, result):
    """Assert the hook denied execution with expected structure."""
    test.assertEqual(result.returncode, 0)
    output = json.loads(result.stdout)
    hook_output = output["hookSpecificOutput"]
    test.assertEqual(hook_output["permissionDecision"], "deny")
    test.assertIn("hookEventName", hook_output)
    test.assertTrue(len(hook_output.get("permissionDecisionReason", "")) > 0)


class TestNoDetection(unittest.TestCase):
    """Tests where the hook should allow execution (no block)."""

    def _run_and_assert_allowed(self, path):
        self.addCleanup(os.unlink, path)
        result = run_hook(path)
        assert_allowed(self, result)

    def test_should_pass_when_no_efficiency_phrase(self):
        path = write_transcript([
            make_assistant_entry("I will fix the bug now."),
        ])
        self._run_and_assert_allowed(path)

    def test_should_pass_when_transcript_does_not_exist(self):
        result = run_hook("/nonexistent/path/transcript.jsonl")
        assert_allowed(self, result)

    def test_should_pass_when_transcript_is_empty(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        )
        f.close()
        self.addCleanup(os.unlink, f.name)

        result = run_hook(f.name)
        assert_allowed(self, result)

    def test_should_pass_when_no_assistant_messages(self):
        path = write_transcript([
            make_user_entry("Fix the bug"),
        ])
        self._run_and_assert_allowed(path)

    def test_should_pass_when_efficiency_phrase_is_in_older_message(self):
        """Only the last assistant message should be checked."""
        path = write_transcript([
            make_assistant_entry("I will work efficiently on this."),
            make_user_entry("OK"),
            make_assistant_entry("Let me fix the first test case."),
        ])
        self._run_and_assert_allowed(path)

    def test_should_pass_when_no_efficiency_phrase_with_trailing_tool_use(self):
        """Text entry has no phrase, followed by tool_use entry."""
        path = write_transcript([
            make_assistant_entry("Let me fix the bug now."),
            make_tool_use_entry(),
        ])
        self._run_and_assert_allowed(path)

    def test_should_pass_when_transcript_path_is_missing(self):
        hook_input = json.dumps({
            "session_id": "test-session",
            "cwd": "/tmp",
            "hook_event_name": "PreToolUse",
        })
        result = subprocess.run(
            ["python3", SCRIPT_PATH],
            input=hook_input,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert_allowed(self, result)


# Each entry: (sub-test label, assistant message text)
DETECTION_CASES = [
    # English
    ("efficiently", "I will handle this efficiently."),
    ("efficient", "This is an efficient approach."),
    ("efficiency", "For efficiency, I will batch these."),
    ("EFFICIENTLY_upper", "EFFICIENTLY handling all tasks."),
    # Japanese
    ("効率的", "効率的に作業を進めます。"),
    ("効率化", "効率化のため一括で修正します。"),
    # Chinese
    ("高效", "高效地处理这些文件。"),
    ("效率", "提高效率是关键。"),
    # German
    ("effizient", "Ich werde das effizient erledigen."),
    ("Effizienz", "Die Effizienz ist wichtig."),
    # French
    ("efficacement", "Je vais traiter cela efficacement."),
    # Spanish / Portuguese
    ("eficientemente", "Voy a hacer esto eficientemente."),
    # Korean
    ("효율적", "효율적으로 작업하겠습니다."),
    # Russian
    ("эффективно", "Я сделаю это эффективно."),
]


class TestDetection(unittest.TestCase):
    """Tests where the hook should block execution."""

    def test_should_block_efficiency_phrases(self):
        for label, message in DETECTION_CASES:
            with self.subTest(phrase=label):
                path = write_transcript([
                    make_assistant_entry(message),
                ])
                self.addCleanup(os.unlink, path)
                result = run_hook(path)
                assert_blocked(self, result)

    def test_should_block_when_text_and_tool_use_are_separate_entries(self):
        """Real transcript structure: text entry followed by tool_use entry."""
        path = write_transcript([
            make_assistant_entry("効率的に作業します。"),
            make_tool_use_entry(),
        ])
        self.addCleanup(os.unlink, path)
        result = run_hook(path)
        assert_blocked(self, result)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions."""

    def test_should_pass_when_invalid_json_input(self):
        result = subprocess.run(
            ["python3", SCRIPT_PATH],
            input="not valid json",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert_allowed(self, result)

    def test_should_pass_when_transcript_has_malformed_lines(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        f.write("not json\n")
        f.write('{"type": "broken"\n')
        f.write(make_assistant_entry("Normal message.") + "\n")
        f.close()
        self.addCleanup(os.unlink, f.name)

        result = run_hook(f.name)
        assert_allowed(self, result)

    def test_should_block_when_phrase_is_substring_of_another_word(self):
        """Substring matching is intentional: 'inefficient' contains
        the pattern 'efficien' and should be blocked.
        This is a known trade-off — false positives on negated forms
        are acceptable because the goal is to catch shortcut-taking language."""
        path = write_transcript([
            make_assistant_entry("The current approach is inefficient."),
        ])
        self.addCleanup(os.unlink, path)
        result = run_hook(path)
        assert_blocked(self, result)


if __name__ == "__main__":
    unittest.main()
