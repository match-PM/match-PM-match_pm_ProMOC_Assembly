# Package Info

Short cheat sheet for the runtime packages.

Use this when you want the fastest answer to:

- where do I start
- where should I change behavior
- why does this file live here

## Runtime Package Shape

The runtime packages use the same main idea:

- `node.py`
- `config.py`
- `models.py`
- `services/`
- `drivers/`
- `algorithms/` when the package has real algorithm code
- `compat/` only if a transition wrapper is still truly needed

This applies to:

- `camera_nodes`
- `linear_axis_nodes`
- `planar_motor_nodes`

## What Goes Where

### `node.py`

Put here:

- ROS node startup
- publishers, subscribers, services, timers
- wiring between ROS and the package internals

Do not put here:

- feature logic
- hardware SDK details
- camera or motion algorithms

Open this first when:

- a service name is wrong
- a topic is wrong
- startup wiring is wrong

### `config.py`

Put here:

- parameter defaults
- typed config objects
- parameter parsing close to startup

Open this first when:

- a parameter is missing
- a default is wrong
- runtime config loading breaks

### `models.py`

Put here:

- shared data models
- small runtime state objects
- enums or simple typed containers used by multiple services

Open this first when:

- shared state is wrong
- a small runtime data type needs to change

### `services/`

Put here:

- ROS service callbacks
- request validation
- feature-specific service logic
- service registration

Typical files:

- `services/autofocus.py`
- `services/mtf.py`
- `services/exposure.py`
- `services/motion.py`
- `services/control.py`
- `services/admin.py`
- `services/status.py`
- `services/validation.py`
- `services/registry.py`

Open this first when:

- a service callback is wrong
- request handling is wrong
- service behavior needs to change

Simple rule:

- service broken -> start in `services/`

### `drivers/`

Put here:

- hardware SDK communication
- real device integration
- simulation or mock backends

Typical files:

- `drivers/hardware.py`
- `drivers/sim.py`
- `drivers/mock.py`
- `drivers/base.py` if a shared driver interface is still useful

Open this first when:

- hardware connection fails
- mock behavior is wrong
- a device API call needs to change

Simple rule:

- hardware or SDK broken -> start in `drivers/`

### `algorithms/`

Only keep this when the package has real algorithm code.

Typical examples:

- camera autofocus algorithms
- focus metrics
- ROI detection
- MTF analysis

Open this first when:

- the camera math or image analysis is wrong
- algorithm strategy should change

Simple rule:

- algorithm broken -> start in `algorithms/`

### `compat/`

Only keep this when we truly still need a transition wrapper.

Rules:

- mark it clearly as compatibility-only
- do not build new features there
- remove it once start paths and tests no longer need it

## Simple Placement Guide

If you are adding...

- a service callback: put it in `services/`
- a hardware or mock backend change: put it in `drivers/`
- a shared runtime enum or state object: put it in `models.py`
- a startup or parameter change: put it in `node.py` or `config.py`
- camera algorithm code: put it in `algorithms/`

## If You Are Unsure

Use this order:

1. service behavior -> `services/`
2. hardware or mock behavior -> `drivers/`
3. shared runtime state -> `models.py`
4. camera algorithm behavior -> `algorithms/`
5. startup wiring -> `node.py`
