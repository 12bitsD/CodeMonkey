"""UserPromptSubmit hook: warn if auth.py still has a hardcoded JWT secret."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

AUTH_FILE = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "backend", "utils", "auth.py"
)
AUTH_FILE = os.path.normpath(AUTH_FILE)

if not os.path.exists(AUTH_FILE):
    sys.exit(0)

content = open(AUTH_FILE, encoding="utf-8").read()

# Flag literal string assignments to SECRET_KEY that don't reference settings/env
hardcoded = re.search(
    r'^SECRET_KEY\s*=\s*["\'][^"\'\n]{4,}["\']',
    content,
    re.MULTILINE,
)

if hardcoded:
    print(json.dumps({
        "systemMessage": (
            "⚠️  L1 WARNING: auth.py has a hardcoded SECRET_KEY literal.\n"
            "    It should read from config.py:  SECRET_KEY = settings.JWT_SECRET_KEY"
        )
    }))
