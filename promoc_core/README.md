# ProMOC Core

## Purpose

`promoc_core` contains shared Python utilities used across runtime node packages.
It is the right place for reusable logic that should not depend on specific nodes.

## How To Run / Build

This is a utility package (no node executable). Validate it via tests/lint:

```bash
make lint
make test-unit
```

Package-level tests:

```bash
colcon test --packages-select promoc_core
colcon test-result --verbose
```

## Key APIs

Core modules:

- `promoc_core/validation.py` (typed validation helpers)
- `promoc_core/conversions.py` (unit and format conversions)
- `promoc_core/motion.py` (motion helper logic)
- `promoc_core/logging.py` (tagged logger helpers)
- `promoc_core/error_handling.py`, `promoc_core/promoc_exceptions.py` (error model)

## Where To Edit

| Goal | Start Here | Then Check |
|---|---|---|
| Add shared validation utility | `promoc_core/promoc_core/validation.py` | package tests under `promoc_core/test/` |
| Add shared conversion helper | `promoc_core/promoc_core/conversions.py` | downstream caller modules |
| Extend error model or recovery helpers | `promoc_core/promoc_core/promoc_exceptions.py` | `promoc_core/promoc_core/error_handling.py`, `promoc_core/ERROR_HANDLING.md` |

## Verify Changes

```bash
make lint
make test-unit
make release-n1-check
```

## Related Docs

- Root onboarding: [`START_HERE.md`](../START_HERE.md)
- Project map: [`docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- Error handling guide: [`promoc_core/ERROR_HANDLING.md`](ERROR_HANDLING.md)
- Quick reference: [`promoc_core/QUICK_REFERENCE.md`](QUICK_REFERENCE.md)

