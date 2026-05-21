"""PostToolUse hook: warn when f-strings are used inside .execute() calls in database.py."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")

if "database.py" not in file_path:
    sys.exit(0)

if not os.path.exists(file_path):
    sys.exit(0)

content = open(file_path, encoding="utf-8").read()

# Find .execute() calls that use f-strings directly
hits = re.findall(r'\.execute\s*\(\s*f["\'].*?["\']', content)

if hits:
    msg = {
        "systemMessage": (
            "⚠️  database.py: f-string detected inside .execute() call.\n"
            "  Ensure whitelist validation guards the interpolated value.\n"
            "  Hits: " + "; ".join(hits)
        )
    }
    print(json.dumps(msg))
