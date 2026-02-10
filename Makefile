# ProMOC Assembly Makefile
# Simple shortcuts for common development tasks

SHELL := /bin/bash

PY_FILES := $(shell git ls-files '*.py')

.PHONY: all build clean sim hardware test lint test-unit check help

all: build

help:
	@echo "Available commands:"
	@echo "  make build     - Build the workspace (colcon build --symlink-install)"
	@echo "  make clean     - Remove build, install, and log directories"
	@echo "  make sim       - Run system in simulation mode"
	@echo "  make hardware  - Run system in hardware mode"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Syntax check all Python files"
	@echo "  make test-unit - Run hardware-independent unit tests"
	@echo "  make check     - Run lint + test-unit"

build:
	colcon build --symlink-install

clean:
	rm -rf build install log

sim:
	source install/setup.bash && ros2 launch promoc_bringup system.launch.py sim_mode:=true

hardware:
	source install/setup.bash && ros2 launch promoc_bringup system.launch.py sim_mode:=false

test:
	colcon test
	colcon test-result --all

lint:
	python -m py_compile $(PY_FILES)

test-unit:
	PYTHONPATH=promoc_core:camera_nodes python -m pytest \
		promoc_core/test/test_validation.py \
		promoc_core/test/test_conversions.py \
		camera_nodes/test/test_autofocus_benchmark.py -q

check: lint test-unit
