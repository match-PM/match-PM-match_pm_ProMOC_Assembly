cmake_minimum_required(VERSION 3.8)
project(promoc_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(promoc_assembly_interfaces REQUIRED)
# --- Gazebo Dependency ---
# Conditionally find Gazebo package based on ROS_DISTRO
if($ENV{ROS_DISTRO} STREQUAL "humble")
  find_package(gazebo_ros REQUIRED)
else()
  # For Jazzy and newer, use ros_gz
  find_package(ros_gz_sim REQUIRED)
endif()
# --- End Gazebo Dependency ---
find_package(ros2_control REQUIRED)
find_package(controller_manager REQUIRED)
find_package(joint_state_broadcaster REQUIRED)
find_package(position_controllers REQUIRED)

# Install launch files, config, and urdf
install(DIRECTORY
  launch
  config
  urdf
  DESTINATION share/${PROJECT_NAME}
)

# Install Python modules
ament_python_install_package(${PROJECT_NAME})

# Install Python executables
install(PROGRAMS
  promoc_bringup/unified_demo.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # Copyright headers aren't consistently present in launch/util scripts.
  # Keep the package lintable by excluding those paths.
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  set(ament_cmake_uncrustify_FOUND TRUE)
  set(ament_cmake_flake8_FOUND TRUE)
  set(ament_cmake_pep257_FOUND TRUE)
  # Exclude specific files from copyright linter.
  set(ament_cmake_copyright_CONFIG_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/.ament_copyright_exclude")
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()