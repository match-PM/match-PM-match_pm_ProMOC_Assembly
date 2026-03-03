# ProMOC Coding Guidelines

## Scope
- Applies to all Python packages in this repository.
- Prioritizes readability for Python beginners and ROS2 newcomers.

## Source Encoding
- Use UTF-8 for all source and documentation files.
- Avoid decorative symbols and emoji in code comments and log messages.
- Prefer plain ASCII log text unless non-ASCII is required by domain content.

## File Structure
- Keep modules focused on one responsibility.
- Keep ROS wiring (subscriptions/services/publishers) separate from domain logic.
- Prefer small helper functions over large monolithic callback bodies.

## Parameters and Config
- Use typed config objects or dedicated loaders for ROS parameters.
- Avoid repeated stringly-typed parameter access in multiple modules.
- Mark legacy parameters explicitly and log deprecation warnings.

## Naming and APIs
- Use consistent canonical namespaces:
  - `/promoc/camera/*`
  - `/promoc/linear_axis/*`
  - `/promoc/mover/*`
- Keep legacy aliases only for migration windows and always log replacement hints.

## Tooling
- Development dependencies are defined in `requirements-dev.txt`.
- Formatting/lint/testing commands are provided by `Makefile`:
  - `make format`
  - `make lint`
  - `make test-unit`
  - `make check`
