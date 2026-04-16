# ProMOC Messstand Makefile
# Simple shortcuts for common development tasks

SHELL := /bin/bash

DEV_PYTHON ?= python
LINT_DIRS := \
	camera_nodes/camera_nodes \
	camera_nodes/test \
	linear_axis_nodes/linear_axis_nodes \
	linear_axis_nodes/test \
	promoc_bringup/promoc_bringup \
	promoc_bringup/launch \
	promoc_bringup/scripts \
	promoc_bringup/test \
	promoc_core/promoc_core \
	promoc_core/test

.PHONY: all build clean hardware hw camera-hw test lint format test-unit release-n1-check release-n-check smoke-hw check install-dev help

all: build

help:
	@echo "Available commands:"
	@echo "  make build     - Build the workspace (colcon build --symlink-install)"
	@echo "  make clean     - Remove build, install, and log directories"
	@echo "  make hw        - Run measurement stand in hardware mode"
	@echo "  make camera-hw - Run camera stack in hardware mode"
	@echo "  make install-dev - Install development dependencies"
	@echo "  make format    - Auto-format Python source with ruff format"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Lint/type/syntax checks for Python"
	@echo "  make test-unit - Run hardware-independent unit tests"
	@echo "  make release-n1-check - Run branch acceptance checks"
	@echo "  make release-n-check  - Alias for release-n1-check"
	@echo "  make smoke-hw  - Print hardware smoke commands"
	@echo "  make check     - Run lint + test-unit + release-n1-check"

build:
	colcon build --symlink-install

clean:
	rm -rf build install log

hardware:
	source install/setup.bash && ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware

hw: hardware

camera-hw:
	source install/setup.bash && ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware

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
	PYTHONPATH=promoc_core:camera_nodes:linear_axis_nodes:promoc_bringup $(DEV_PYTHON) -m pytest \
		promoc_core/test/test_validation.py \
		promoc_core/test/test_error_handling.py \
		promoc_core/test/test_logging.py \
		camera_nodes/test/test_config.py \
		camera_nodes/test/test_handlers_exposure.py \
		camera_nodes/test/test_handlers_mtf.py \
		camera_nodes/test/test_handlers_autofocus.py \
		camera_nodes/test/test_autofocus_refactor_contract.py \
		camera_nodes/test/test_camera_namespace_contract.py \
		linear_axis_nodes/test/test_motion_adapter.py \
		linear_axis_nodes/test/test_service_callbacks_regression.py \
		linear_axis_nodes/test/test_linear_axis_namespace_contract.py \
		promoc_bringup/test/test_system_launch.py \
		promoc_bringup/test/test_launch_runtime_mode.py \
		promoc_bringup/test/test_hardware_launch_smoke.py \
		promoc_bringup/test/test_hardware_first_cleanup.py \
		promoc_bringup/test/test_release_n_check.py \
		camera_nodes/test/test_autofocus_benchmark.py -q

release-n1-check:
	$(DEV_PYTHON) promoc_bringup/scripts/release_n_check.py

release-n-check: release-n1-check

smoke-hw:
	$(DEV_PYTHON) promoc_bringup/scripts/release_n_smoke.py --mode hardware

check: lint test-unit release-n1-check
