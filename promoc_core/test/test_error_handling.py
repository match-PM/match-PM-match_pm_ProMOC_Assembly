"""Unit tests for retry behavior in promoc_core.error_handling."""

from __future__ import annotations

import pytest

from promoc_core.error_handling import RetryConfig, retry_on_error


def test_retry_on_error_retries_until_success() -> None:
    calls = {"count": 0}

    @retry_on_error(
        RetryConfig(
            max_attempts=3,
            delay=0.0,
            backoff_factor=1.0,
            max_delay=0.0,
            retriable_exceptions=(RuntimeError,),
        )
    )
    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    assert flaky() == "ok"
    assert calls["count"] == 3


def test_retry_on_error_raises_last_exception_after_max_attempts() -> None:
    calls = {"count": 0}

    @retry_on_error(
        RetryConfig(
            max_attempts=2,
            delay=0.0,
            backoff_factor=1.0,
            max_delay=0.0,
            retriable_exceptions=(RuntimeError,),
        )
    )
    def always_fail() -> None:
        calls["count"] += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        always_fail()

    assert calls["count"] == 2


@pytest.mark.parametrize(
    ("max_attempts", "delay", "backoff_factor", "max_delay"),
    [
        (0, 0.0, 1.0, 0.0),
        (1, -1.0, 1.0, 0.0),
        (1, 0.0, 0.0, 0.0),
        (1, 0.0, 1.0, -1.0),
    ],
)
def test_retry_on_error_rejects_invalid_config(
    max_attempts: int,
    delay: float,
    backoff_factor: float,
    max_delay: float,
) -> None:
    with pytest.raises(ValueError):
        retry_on_error(
            RetryConfig(
                max_attempts=max_attempts,
                delay=delay,
                backoff_factor=backoff_factor,
                max_delay=max_delay,
                retriable_exceptions=(RuntimeError,),
            )
        )
