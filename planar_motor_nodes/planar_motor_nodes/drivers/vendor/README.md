# Local PMCLib Vendor Directory

Place the proprietary planar-motor PMCLib package here for hardware mode:

```text
planar_motor_nodes/planar_motor_nodes/drivers/vendor/pmclib/
```

This directory is local-only. Do not commit proprietary vendor contents.

Mock mode does not require this directory. Hardware mode loads PMCLib lazily and
may also require `pythonnet`/`clr`, depending on the vendor package.
