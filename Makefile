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
	promoc_bringup/test \
	promoc_core/promoc_core \
	promoc_core/test

.PHONY: all build clean hardware hw test lint format test-unit check install-dev help

all: build

help:
	@echo "Available commands:"
	@echo "  make build     - Build the workspace (colcon build --symlink-install)"
	@echo "  make clean     - Remove build, install, and log directories"
	@echo "  make hw        - Run measurement stand in hardware mode"
	@echo "  make install-dev - Install development dependencies"
	@echo "  make format    - Auto-format Python source with ruff format"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Lint/type/syntax checks for Python"
	@echo "  make test-unit - Run hardware-independent unit tests"
	@echo "  make check     - Run lint + test-unit"

build:
	colcon build --symlink-install

clean:
	rm -rf build install log

hardware:
	source install/setup.bash && ros2 launch promoc_bringup optical_measurement_system.launch.py

hw: hardware

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
		camera_nodes/test/test_mtf_raw_bayer.py \
		camera_nodes/test/test_mtf_param_mapping.py \
		camera_nodes/test/test_mtf_debug_export.py \
		linear_axis_nodes/test/test_motion_adapter.py \
		linear_axis_nodes/test/test_service_callbacks_regression.py \
		linear_axis_nodes/test/test_linear_axis_namespace_contract.py -q

check: lint test-unit
