cmake_minimum_required(VERSION 3.10)
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
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Check ROS 2 distribution
# needed because jazzy needs this two dependencies but humble doesnt
if(NOT $ENV{ROS_DISTRO} STREQUAL "humble")
  find_package(service_msgs REQUIRED)
  set(ADDITIONAL_DEPENDENCIES service_msgs)
endif()

set(INTERFACE_FILES
  "msg/DeviceStatus.msg"
  "msg/SystemStatus.msg"
  "msg/planar_motor/XBotInfo.msg"
  "srv/planar_motor/ActivateXbots.srv"
  "srv/planar_motor/ArcMotionSi.srv"
  "srv/planar_motor/LevitationXbots.srv"
  "srv/planar_motor/LinearMotionSi.srv"
  "srv/planar_motor/RotaryMotion.srv"
  "srv/planar_motor/SixDofMotion.srv"
  "srv/planar_motor/StopMotion.srv"
  "srv/planar_motor/SetVelocityAcceleration.srv"
  "msg/linear_axis/LinearAxisInfo.msg"
  "srv/linear_axis/MoveAbsolute.srv"
  "srv/linear_axis/MoveRelative.srv"
  "srv/linear_axis/Home.srv"
  "srv/linear_axis/ShutdownLinearAxis.srv"
  "srv/linear_axis/GetPosition.srv"
  "srv/linear_axis/GetOperationStatus.srv"
  "srv/linear_axis/GetSetHomingParams.srv"
  "srv/linear_axis/SetVelocityParameters.srv"
  "srv/linear_axis/GetVelocityParameters.srv"
  "srv/linear_axis/EmergencyStop.srv"
  "srv/linear_axis/JogAxis.srv"
  "srv/linear_axis/Stop.srv"
  "srv/linear_axis/SetJogParameters.srv"
  "srv/linear_axis/GetJogParameters.srv"
  "srv/camera/SetExposure.srv"
  "srv/camera/AutoFocus.srv"
)

# CRITICAL: Generate the interfaces (this was missing!)
rosidl_generate_interfaces(${PROJECT_NAME}
  ${INTERFACE_FILES}
  DEPENDENCIES builtin_interfaces ${ADDITIONAL_DEPENDENCIES}
)

# Export dependencies for downstream packages
ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # Avoid network-dependent schema fetches in offline handover environments.
  set(ament_cmake_xmllint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
