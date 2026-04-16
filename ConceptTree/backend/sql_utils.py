from __future__ import annotations

import re


_DOLLAR_TAG_RE = re.compile(r"\$[A-Za-z0-9_]*\$")


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    dollar_tag: str | None = None
    i = 0

    while i < len(sql):
        if dollar_tag:
            if sql.startswith(dollar_tag, i):
                current.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            current.append(sql[i])
            i += 1
            continue

        ch = sql[i]

        if in_single_quote:
            current.append(ch)
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    current.append(sql[i + 1])
                    i += 2
                    continue
                in_single_quote = False
            i += 1
            continue

        if ch == "'":
            in_single_quote = True
            current.append(ch)
            i += 1
            continue

        if ch == "$":
            match = _DOLLAR_TAG_RE.match(sql, i)
            if match:
                dollar_tag = match.group(0)
                current.append(dollar_tag)
                i = match.end()
                continue

        if ch == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    return statements
