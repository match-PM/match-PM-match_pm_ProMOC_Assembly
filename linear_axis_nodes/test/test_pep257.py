"""Legacy ament_pep257 gate is disabled.

Repository style checks are unified via Ruff in `make lint`.
Keeping this test as a no-op avoids duplicate style systems.
"""


def test_pep257() -> None:
    """No-op: style checks are handled by Ruff in the top-level Makefile."""
    assert True
