"""Shared slowapi rate limiter instance — import this everywhere."""
import starlette.config

# Patch starlette.config to read files with UTF-8 on Windows (default is GBK).
# slowapi's Limiter calls starlette.config.Config(".env") on import.
_orig_read_file = starlette.config.Config._read_file


def _utf8_read_file(self, file_name):
    import io, os

    file_values: dict[str, str] = {}
    if not file_name or not os.path.isfile(file_name):
        return file_values
    with io.open(file_name, encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            file_values[k.strip()] = v.strip().strip('"').strip("'")
    return file_values


starlette.config.Config._read_file = _utf8_read_file

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
