# Test Fixtures

This directory contains non-runtime helper code and data used for tests and
algorithm validation.

- `synthetic_targets.py`: synthetic slanted-edge and square target generators
  for hardware-independent MTF unit tests.

Do not import these helpers from production runtime modules under
`camera_nodes/camera_nodes/`.
