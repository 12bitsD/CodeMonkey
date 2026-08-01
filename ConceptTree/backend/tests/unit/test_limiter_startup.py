import importlib


def test_rate_limiter_initializes_with_current_starlette():
    module = importlib.import_module("utils.limiter")
    assert module.limiter is not None
