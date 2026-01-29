<p align="center">
  <img src="assets/metronome-banner.jpg" width="600" alt="metronome">
</p>

# metronome

A Claude Code plugin that prevents Claude from taking shortcuts on repetitive tasks.

## Problem

When Claude encounters repetitive tasks, it tends to declare "I'll work efficiently" and then:
- Switches from step-by-step edits to bulk operations (e.g. `sed` one-liners)
- Breaks files, then runs `git checkout` to revert—losing unrelated uncommitted changes too

**Example**: Asked to fix comments across 20 files one by one, Claude processes 5 files correctly, then announces "I'll handle the rest efficiently." It runs a `sed` command that corrupts files, notices the breakage, and runs `git checkout` to undo everything—including your other uncommitted changes.

This plugin detects such declarations and blocks the Bash tool call, reminding Claude to slow down.

## Detected Phrases

| Language | Pattern | Matches |
|----------|---------|---------|
| English | efficien | efficient, efficiently, efficiency |
| 日本語 | 効率 | 効率的, 効率化 |
| 中文 | 高效, 效率 | (2 patterns required) |
| Deutsch | effizien | effizient, Effizienz |
| Français | efficac | efficace, efficacement, efficacité |
| Español / Português | eficien | eficiente, eficientemente, eficiencia |
| 한국어 | 효율 | 효율적으로, 효율화 |
| Русский | эффектив | эффективно, эффективность |

## Guidance

When triggered, Claude receives:

```
Slow down.

Read the current task, execute it, verify the result, then move to the next.
```

No prohibitions. Only positive instructions.

## Installation

> Requires [Claude Code](https://claude.ai/code) (this is a Claude Code plugin)

```bash
# 1. Start Claude Code
claude

# 2. Install the marketplace
/plugin marketplace add shinpr/metronome

# 3. Install plugin
/plugin install metronome@metronome

# 4. Restart session (required)
# Exit and restart Claude Code
```

## Structure

```
metronome/                        # marketplace root
├── .claude-plugin/
│   └── marketplace.json
├── metronome/                    # plugin
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── hooks/
│   │   └── hooks.json
│   └── scripts/
│       └── check-efficiency.py
├── tests/
│   └── test_check_efficiency.py
└── README.md
```

## Requirements

- Claude Code 1.0.33+
- Python 3

## License

MIT
