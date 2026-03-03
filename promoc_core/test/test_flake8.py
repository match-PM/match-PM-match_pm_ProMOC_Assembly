"""Legacy ament_flake8 gate is disabled.

Repository linting is unified via Ruff in `make lint`.
Keeping this test as a no-op avoids duplicate lint systems.
"""


def test_flake8() -> None:
    """No-op: linting is handled by Ruff in the top-level Makefile."""
    assert True
