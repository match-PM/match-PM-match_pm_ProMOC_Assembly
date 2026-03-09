# ProMOC Core

## Purpose

`promoc_core` owns reusable Python logic that should be shared across packages without depending on runtime nodes.

## What Belongs Here

Good fits for `promoc_core`:

- validation helpers
- conversions
- logging helpers
- shared error models
- reusable motion or math helpers that are not package-specific

Do not move runtime-node-specific behavior into `promoc_core`.

## How To Verify

```bash
make lint
make test-unit
```

Package-only check:

```bash
colcon test --packages-select promoc_core
colcon test-result --verbose
```

## Where To Edit Common Changes

| Goal | Open this first |
|---|---|
| Add shared validation logic | `promoc_core/promoc_core/validation.py` |
| Add shared conversion logic | `promoc_core/promoc_core/conversions.py` |
| Extend shared motion helpers | `promoc_core/promoc_core/motion.py` |
| Extend logging helpers | `promoc_core/promoc_core/logging.py` |
| Extend error handling | `promoc_core/promoc_core/promoc_exceptions.py`, `promoc_core/promoc_core/error_handling.py` |

## Related Docs

- onboarding: [`../docs/START_HERE.md`](../docs/START_HERE.md)
- structure map: [`../docs/PROJECT_STRUCTURE.md`](../docs/PROJECT_STRUCTURE.md)
- architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- error handling guide: [`ERROR_HANDLING.md`](ERROR_HANDLING.md)
- quick reference: [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md)
