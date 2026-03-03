# ProMOC Assembly Makefile
# Simple shortcuts for common development tasks

SHELL := /bin/bash

DEV_PYTHON ?= python
LINT_PATHS := \
	camera_nodes/camera_nodes/camera_node.py \
	camera_nodes/camera_nodes/config.py \
	camera_nodes/camera_nodes/mtf_param_mapping.py \
	camera_nodes/camera_nodes/parameter_access.py \
	camera_nodes/camera_nodes/services.py \
	camera_nodes/camera_nodes/handlers \
	linear_axis_nodes/linear_axis_nodes/lts300_node.py \
	planar_motor_nodes/planar_motor_nodes/mover_node.py \
	promoc_bringup/promoc_bringup/launch_utils.py \
	promoc_bringup/launch/system.launch.py \
	promoc_bringup/launch/camera.launch.py \
	promoc_bringup/launch/optical_measurement_system.launch.py \
	promoc_bringup/scripts/release_n_check.py \
	promoc_bringup/scripts/release_n_smoke.py \
	camera_nodes/test/test_config.py \
	camera_nodes/test/test_handlers_exposure.py \
	camera_nodes/test/test_handlers_mtf.py \
	camera_nodes/test/test_handlers_autofocus.py \
	camera_nodes/test/test_service_namespace_migration.py \
	linear_axis_nodes/test/test_linear_axis_namespace_migration.py \
	planar_motor_nodes/test/test_mover_namespace_migration.py \
	promoc_bringup/test/test_system_launch.py \
	promoc_bringup/test/test_launch_runtime_mode.py \
	promoc_bringup/test/test_release_n_check.py

.PHONY: all build clean sim hardware hw camera-hw doctor-hw test lint format test-unit release-n-check smoke-sim smoke-hw check install-dev help

all: build

help:
	@echo "Available commands:"
	@echo "  make build     - Build the workspace (colcon build --symlink-install)"
	@echo "  make clean     - Remove build, install, and log directories"
	@echo "  make doctor-hw - Hardware readiness checks"
	@echo "  make hw        - Run full system in hardware mode (official path)"
	@echo "  make camera-hw - Run camera stack in hardware mode"
	@echo "  make sim       - Optional/experimental simulation path"
	@echo "  make install-dev - Install development dependencies"
	@echo "  make format    - Auto-format Release-N Python files (ruff format)"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Lint/type/syntax checks for Python"
	@echo "  make test-unit - Run hardware-independent unit tests"
	@echo "  make release-n-check - Run automated Release-N acceptance checks"
	@echo "  make smoke-sim - Print simulation smoke commands"
	@echo "  make smoke-hw  - Print hardware smoke commands"
	@echo "  make check     - Run lint + test-unit + release-n-check"

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
	$(DEV_PYTHON) -m ruff check $(LINT_PATHS)
	$(DEV_PYTHON) -m ruff format --check $(LINT_PATHS)
	@set -e; \
	files=$$(for p in $(LINT_PATHS); do \
		if [ -d "$$p" ]; then find "$$p" -type f -name '*.py'; \
		elif [ -f "$$p" ]; then echo "$$p"; \
		fi; \
	done); \
	if [ -n "$$files" ]; then $(DEV_PYTHON) -m py_compile $$files; fi

format:
	$(DEV_PYTHON) -m ruff format $(LINT_PATHS)

test-unit:
	PYTHONPATH=promoc_core:camera_nodes $(DEV_PYTHON) -m pytest \
		promoc_core/test/test_validation.py \
		promoc_core/test/test_conversions.py \
		camera_nodes/test/test_config.py \
		camera_nodes/test/test_handlers_exposure.py \
		camera_nodes/test/test_handlers_mtf.py \
		camera_nodes/test/test_handlers_autofocus.py \
		camera_nodes/test/test_service_namespace_migration.py \
		linear_axis_nodes/test/test_linear_axis_namespace_migration.py \
		planar_motor_nodes/test/test_mover_namespace_migration.py \
		promoc_bringup/test/test_system_launch.py \
		promoc_bringup/test/test_launch_runtime_mode.py \
		promoc_bringup/test/test_release_n_check.py \
		camera_nodes/test/test_autofocus_benchmark.py -q

release-n-check:
	$(DEV_PYTHON) promoc_bringup/scripts/release_n_check.py

smoke-sim:
	$(DEV_PYTHON) promoc_bringup/scripts/release_n_smoke.py --mode sim

smoke-hw:
	$(DEV_PYTHON) promoc_bringup/scripts/release_n_smoke.py --mode hardware

check: lint test-unit release-n-check
