"""Shared fixtures for pure unit tests that run without a real database.

Unit tests in this directory mock out all external dependencies (database,
LLM, HTTP) and therefore do not need the full integration-test setup
provided by ``tests/conftest.py``.

The ``reset_database`` fixture here overrides the session-level one from
the parent conftest, replacing it with a no-op so that unit tests are
never accidentally blocked waiting for a Postgres connection.
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture(autouse=True)
def reset_database():
    """Override the parent reset_database fixture with a no-op.

    Unit tests mock the database layer, so there is nothing to truncate
    or re-seed. This fixture prevents the integration-level database reset
    from running, keeping unit tests fast and free of infrastructure
    dependencies.
    """
    yield
