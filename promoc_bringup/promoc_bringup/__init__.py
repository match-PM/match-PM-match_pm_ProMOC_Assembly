"""
ProMOC Bringup - Launch Files and Demo Utilities
=================================================

This package provides launch files, configuration, and demo controllers
for the ProMOC Assembly system.

Modules:
    - unified_demo: Configurable demo controller for all modes
    - service_helper: Reusable service call utilities

Quick Start:
    # Launch full system
    ros2 launch promoc_bringup system.launch.py
    
    # Launch with simulation mode
    ros2 launch promoc_bringup system.launch.py sim_mode:=true
    
    # Run unified demo
    ros2 run promoc_bringup unified_demo --ros-args -p demo_mode:=full

Launch Files:
    - system.launch.py: Full system (camera, mover, linear axes)
    - camera.launch.py: Camera only (sim or hardware)
    - planar_motor_demo.launch.py: Planar motor demo
    - promoc_assembly_demo.launch.py: Full demo with controller

Configuration Files (config/):
    - mover_node_params.yaml: Planar motor settings
    - linear_axes_params.yaml: Linear axis settings
    - camera_node_params.yaml: Camera settings
    - demo_controller_params.yaml: Demo settings
"""
