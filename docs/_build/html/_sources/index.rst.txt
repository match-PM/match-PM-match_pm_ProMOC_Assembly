
ProMOC Assembly Documentation
=============================

Welcome to the **ProMOC Assembly** documentation! This project provides a modular ROS2 system for precision assembly tasks using linear axes (Thorlabs LTS300) and planar motor systems.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation/index
   quickstart/index
   tutorials/index

.. toctree::
   :maxdepth: 2
   :caption: System Architecture

   architecture/overview
   architecture/hardware
   architecture/software
   architecture/interfaces

.. toctree::
   :maxdepth: 2
   :caption: Hardware Components

   hardware/linear_axes
   hardware/planar_motor
   hardware/sensors
   hardware/safety

.. toctree::
   :maxdepth: 2
   :caption: ROS2 Packages

   packages/linear_axis_nodes
   packages/planar_motor_nodes
   packages/promoc_assembly_interfaces
   packages/promoc_bringup

.. toctree::
   :maxdepth: 2
   :caption: Simulation & Testing

   simulation/gazebo
   simulation/urdf
   simulation/testing

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/linear_axis_nodes
   api/planar_motor_nodes
   api/interfaces
   api/utilities

.. toctree::
   :maxdepth: 2
   :caption: Development

   development/contributing
   development/coding_standards
   development/testing
   development/debugging

.. toctree::
   :maxdepth: 1
   :caption: Appendix

   appendix/troubleshooting
   appendix/faq
   appendix/glossary
   appendix/changelog

```


Quick Navigation
---------------

**🚀 New Users**

- Installation guide: :doc:`installation/index`
- Quickstart: :doc:`quickstart/index`
- Tutorials: :doc:`tutorials/index`

**🔧 Developers**

- Linear axis API: :doc:`api/linear_axis_nodes`
- Planar motor API: :doc:`api/planar_motor_nodes`
- Contributing: :doc:`development/contributing`

**🎯 System Integrators**

- System architecture: :doc:`architecture/overview`
- Hardware setup: :doc:`hardware/linear_axes`
- Simulation: :doc:`simulation/gazebo`

Project Overview
---------------

The **ProMOC Assembly** system is designed for high-precision assembly tasks in research and industrial environments. It combines:

- **Linear Axes**: Thorlabs LTS300 with nanometer precision
- **Planar Motor**: High-speed 2D positioning system
- **Modular Design**: Easy integration of additional components
- **ROS2 Integration**: Industry-standard robotics middleware
- **Simulation Support**: Full Gazebo simulation environment

Key Features
------------

- ✅ **Modular Architecture** - Easy to extend and maintain
- ✅ **Hardware Abstraction** - Seamless sim-to-real transfer
- ✅ **Safety Systems** - Collision detection and limits
- ✅ **High Precision** - Sub-micrometer positioning
- ✅ **Real-time Control** - Deterministic motion control
- ✅ **ROS2 Native** - Standard interfaces and tools

System Requirements
-------------------

- **OS**: Ubuntu 20.04/22.04/24.04 LTS
- **ROS2**: Humble Hawksbill or newer
- **Python**: 3.8+
- **Hardware**: Thorlabs LTS300, PMCLib-compatible planar motor

Support
-------

- 📖 **Documentation**: This site
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions
- 📧 **Contact**: ProMOC Assembly Team

.. note::

   This documentation is automatically generated from the source code and maintained alongside the project development.
