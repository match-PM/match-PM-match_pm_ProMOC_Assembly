# ProMOC Assembly convenience commands

SHELL := /bin/bash

REPO_ROOT := $(abspath .)
WORKSPACE_ROOT ?= $(abspath ../..)

.PHONY: help build clean test check check-quick check-full mock hardware

help:
	@echo "Available commands:"
	@echo "  make build        - Build the ROS workspace from WORKSPACE_ROOT"
	@echo "  make clean        - Remove build/install/log in WORKSPACE_ROOT"
	@echo "  make test         - Run colcon tests from WORKSPACE_ROOT"
	@echo "  make check        - Run the quick project check"
	@echo "  make check-quick  - Run python3 tools/check_project.py --quick"
	@echo "  make check-full   - Run the full project check with WORKSPACE_ROOT"
	@echo "  make mock         - Launch the full system in mock mode"
	@echo "  make hardware     - Launch the full system in hardware mode"
	@echo ""
	@echo "Default WORKSPACE_ROOT assumes this repo lives in <workspace>/src/."

build:
	cd "$(WORKSPACE_ROOT)" && colcon build --symlink-install

clean:
	cd "$(WORKSPACE_ROOT)" && rm -rf build install log

test:
	cd "$(WORKSPACE_ROOT)" && colcon test && colcon test-result --verbose

check: check-quick

check-quick:
	cd "$(REPO_ROOT)" && python3 tools/check_project.py --quick

check-full:
	cd "$(REPO_ROOT)" && python3 tools/check_project.py --full --workspace-root "$(WORKSPACE_ROOT)"

mock:
	cd "$(WORKSPACE_ROOT)" && source install/setup.bash && ros2 launch promoc_bringup system.launch.py driver_mode:=mock

hardware:
	cd "$(WORKSPACE_ROOT)" && source install/setup.bash && ros2 launch promoc_bringup system.launch.py driver_mode:=hardware
