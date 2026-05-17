"""PreToolUse hook: block writes to .env files (allow .env.example)."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")

if ".env" in file_path and ".env.example" not in file_path:
    print(json.dumps({
        "continue": False,
        "stopReason": (
            "BLOCKED: Writing to .env is not allowed.\n"
            "- Put placeholder values in .env.example instead.\n"
            "- The real .env is managed manually outside version control."
        )
    }))
    sys.exit(2)
