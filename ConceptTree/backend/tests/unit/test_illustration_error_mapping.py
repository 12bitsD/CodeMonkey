from __future__ import annotations

import pytest

from routers.deep_learn import _illustration_failure_detail


class ProviderFailure(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@pytest.mark.no_db
@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (ProviderFailure("API key expired: sk-secret", 401), "IMAGE_AUTH_FAILED"),
        (ProviderFailure("insufficient credit", 402), "IMAGE_CREDIT_EXHAUSTED"),
        (ProviderFailure("rate limit exceeded", 429), "IMAGE_RATE_LIMITED"),
        (ProviderFailure("request timed out", 504), "IMAGE_TIMEOUT"),
        (ProviderFailure("storage upload permission denied"), "IMAGE_STORAGE_FAILED"),
        (ProviderFailure("no image data in response"), "IMAGE_RESPONSE_INVALID"),
    ],
)
def test_illustration_errors_are_actionable_without_leaking_provider_details(failure, code):
    detail = _illustration_failure_detail(failure)

    assert detail["code"] == code
    assert detail["message"]
    assert "sk-secret" not in detail["message"]
