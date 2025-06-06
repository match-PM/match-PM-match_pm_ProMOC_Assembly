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
find_package(rclcpp REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Check ROS 2 distribution
# needed because jazzy needs this two dependencies but humble doesnt
if(NOT $ENV{ROS_DISTRO} STREQUAL "humble")
  find_package(service_msgs REQUIRED)
  set(ADDITIONAL_DEPENDENCIES service_msgs)
endif()

set(INTERFACE_FILES
  "msg/planar_motor/XBotInfo.msg"
  "srv/planar_motor/ActivateXbots.srv"
  "srv/planar_motor/ArcMotionTargetRadius.srv"
  "srv/planar_motor/LevitationXbots.srv"
  "srv/planar_motor/LinearMotionSi.srv"
  "srv/planar_motor/RotaryMotion.srv"
  "srv/planar_motor/SixDofMotion.srv"
  "srv/planar_motor/StopMotion.srv"
  "srv/planar_motor/SetVelocityAcceleration.srv"
  "msg/test/Test.msg"
  "msg/linear_axis/LinearAxisInfo.msg"
  "srv/linear_axis/MoveAbsolute.srv"
  "srv/linear_axis/MoveRelativ.srv"
  "srv/linear_axis/Home.srv"
  "srv/linear_axis/ShutdownLinearAxis.srv"
  "srv/linear_axis/GetPosition.srv"
  "srv/linear_axis/GetSetHomingParams.srv"
  "srv/linear_axis/GetSetVelocityParams.srv"
)

if(NOT $ENV{ROS_DISTRO} STREQUAL "humble")
  rosidl_generate_interfaces(${PROJECT_NAME}
    ${INTERFACE_FILES}
    DEPENDENCIES ${ADDITIONAL_DEPENDENCIES}
  )
else()
  rosidl_generate_interfaces(${PROJECT_NAME}
    ${INTERFACE_FILES}
  )
endif()

ament_export_dependencies(rosidl_default_runtime)

ament_package()
