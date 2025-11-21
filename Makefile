# ProMOC Assembly Makefile
# Simple shortcuts for common development tasks

SHELL := /bin/bash

.PHONY: all build clean sim hardware test help

all: build

help:
	@echo "Available commands:"
	@echo "  make build     - Build the workspace (colcon build --symlink-install)"
	@echo "  make clean     - Remove build, install, and log directories"
	@echo "  make sim       - Run system in simulation mode"
	@echo "  make hardware  - Run system in hardware mode"
	@echo "  make test      - Run tests"

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
