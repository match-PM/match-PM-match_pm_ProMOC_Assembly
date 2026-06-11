# ProMOC Assembly Makefile
# Simple shortcuts for the maintained CS runtime workflow

SHELL := /bin/bash

DEV_PYTHON ?= python
LINT_DIRS := \
	camera_nodes/camera_nodes \
	camera_nodes/test \
	linear_axis_nodes/linear_axis_nodes \
	linear_axis_nodes/test \
	planar_motor_nodes/planar_motor_nodes \
	planar_motor_nodes/test \
	promoc_bringup/promoc_bringup \
	promoc_bringup/launch \
	promoc_bringup/scripts \
	promoc_bringup/test

.PHONY: all build clean sim hardware hw camera-hw doctor-hw test lint format test-unit cs-runtime-check cs-runtime-smoke-sim cs-runtime-smoke-hw check install-dev help
all: build

help:
	@echo "Available commands:"
	@echo "  make build              - Build the workspace (colcon build --symlink-install)"
	@echo "  make clean              - Remove build, install, and log directories"
	@echo "  make doctor-hw          - Hardware readiness checks"
	@echo "  make hw                 - Run full system in hardware mode (official path)"
	@echo "  make camera-hw          - Secondary camera-only hardware path"
	@echo "  make sim                - Secondary simulation path"
	@echo "  make install-dev        - Install development dependencies"
	@echo "  make format             - Auto-format Python source with ruff format"
	@echo "  make test               - Run tests"
	@echo "  make lint               - Lint/type/syntax checks for Python"
	@echo "  make test-unit          - Run hardware-independent unit tests"
	@echo "  make cs-runtime-check   - Run automated CS runtime acceptance checks"
	@echo "  make cs-runtime-smoke-sim - Print simulation smoke commands"
	@echo "  make cs-runtime-smoke-hw  - Print hardware smoke commands"
	@echo "  make check              - Run lint + test-unit + cs-runtime-check"
build:
	colcon build --symlink-install

clean:
	rm -rf build install log

sim:
	source install/setup.bash && ros2 launch promoc_bringup system.launch.py runtime_mode:=sim

hardware:
	source install/setup.bash && ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware

hw: hardware

camera-hw:
	source install/setup.bash && ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware

doctor-hw:
	./setup/check_installation.sh

install-dev:
	$(DEV_PYTHON) -m pip install -r requirements-dev.txt

test:
	colcon test
	colcon test-result --all

lint:
	$(DEV_PYTHON) -m ruff check $(LINT_DIRS)
	$(DEV_PYTHON) -m ruff format --check $(LINT_DIRS)
	@set -e; \
	files=$$(for p in $(LINT_DIRS); do \
		if [ -d "$$p" ]; then find "$$p" -type f -name '*.py'; \
		elif [ -f "$$p" ]; then echo "$$p"; \
		fi; \
	done); \
	if [ -n "$$files" ]; then $(DEV_PYTHON) -m py_compile $$files; fi

format:
	$(DEV_PYTHON) -m ruff format $(LINT_DIRS)

test-unit:
	PYTHONPATH=promoc_core:camera_nodes:linear_axis_nodes:planar_motor_nodes:promoc_bringup $(DEV_PYTHON) -m pytest \
		promoc_core/test/test_validation.py \
		promoc_core/test/test_conversions.py \
		camera_nodes/test/test_config.py \
		camera_nodes/test/test_handlers_exposure.py \
		camera_nodes/test/test_handlers_autofocus.py \
		camera_nodes/test/test_autofocus_refactor_contract.py \
		camera_nodes/test/test_camera_namespace_contract.py \
		linear_axis_nodes/test/test_linear_axis_namespace_contract.py \
		planar_motor_nodes/test/test_mover_namespace_contract.py \
		promoc_bringup/test/test_system_launch.py \
		promoc_bringup/test/test_launch_runtime_mode.py \
		promoc_bringup/test/test_hardware_first_cleanup.py \
		promoc_bringup/test/test_cs_runtime_check.py -q

cs-runtime-check:
	$(DEV_PYTHON) promoc_bringup/scripts/cs_runtime_check.py

cs-runtime-smoke-sim:
	$(DEV_PYTHON) promoc_bringup/scripts/cs_runtime_smoke.py --mode sim

cs-runtime-smoke-hw:
	$(DEV_PYTHON) promoc_bringup/scripts/cs_runtime_smoke.py --mode hardware

check: lint test-unit cs-runtime-check