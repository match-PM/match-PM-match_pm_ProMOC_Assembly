# ProMOC Assembly convenience commands

SHELL := /bin/bash

REPO_ROOT := $(abspath .)
ifeq ($(notdir $(REPO_ROOT)),src)
WORKSPACE_ROOT ?= $(abspath ..)
WORKSPACE_SETUP ?= ../install/setup.bash
else
WORKSPACE_ROOT ?= $(abspath ../..)
WORKSPACE_SETUP ?= ../../install/setup.bash
endif

.PHONY: help build clean test check validate start-mock start-hardware mock hardware

help:
	@echo "Available commands:"
	@echo "  make build        - Build the ROS workspace from WORKSPACE_ROOT"
	@echo "  make clean        - Remove build/install/log in WORKSPACE_ROOT"
	@echo "  make test         - Run colcon tests from WORKSPACE_ROOT"
	@echo "  make check        - Run setup/setup.py validate"
	@echo "  make validate     - Compatibility alias for check"
	@echo "  make start-mock     - Launch the device stack without hardware"
	@echo "  make start-hardware - Launch the device stack with real hardware"
	@echo "  make mock           - Compatibility alias for start-mock"
	@echo "  make hardware       - Compatibility alias for start-hardware"
	@echo ""
	@echo "WORKSPACE_ROOT=$(WORKSPACE_ROOT)"

build:
	cd "$(WORKSPACE_ROOT)" && colcon build --symlink-install

clean:
	cd "$(WORKSPACE_ROOT)" && rm -rf build install log

test:
	cd "$(WORKSPACE_ROOT)" && colcon test && colcon test-result --verbose

check:
	cd "$(REPO_ROOT)" && python3 setup/setup.py validate

validate: check

start-mock:
	cd "$(WORKSPACE_ROOT)" && source install/setup.bash && ros2 launch promoc_bringup system.launch.py driver_mode:=mock

start-hardware:
	cd "$(WORKSPACE_ROOT)" && source install/setup.bash && ros2 launch promoc_bringup system.launch.py driver_mode:=hardware

mock: start-mock

hardware: start-hardware
