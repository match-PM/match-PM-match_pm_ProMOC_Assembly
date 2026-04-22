cmake_minimum_required(VERSION 3.8)
project(promoc_assembly_interfaces)

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Check ROS 2 distribution
# needed because jazzy needs this two dependencies but humble doesnt
if(NOT $ENV{ROS_DISTRO} STREQUAL "humble")
  find_package(service_msgs REQUIRED)
  set(ADDITIONAL_DEPENDENCIES service_msgs)
endif()

# Keep the package definition in sync with the filesystem after interface refactors.
file(GLOB_RECURSE INTERFACE_FILES
  RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}"
  "msg/*.msg"
  "srv/*.srv"
)
list(SORT INTERFACE_FILES)

if(NOT INTERFACE_FILES)
  message(FATAL_ERROR "No ROS interface files found under msg/ or srv/")
endif()

rosidl_generate_interfaces(${PROJECT_NAME}
  ${INTERFACE_FILES}
  DEPENDENCIES ${ADDITIONAL_DEPENDENCIES}
)

# Export dependencies for downstream packages
ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
