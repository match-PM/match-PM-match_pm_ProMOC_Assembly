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
find_package(service_msgs REQUIRED)


rosidl_generate_interfaces(${PROJECT_NAME}
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
  "srv/linear_axis/MoveTo.srv"
  "srv/linear_axis/Home.srv"
  DEPENDENCIES service_msgs
)


ament_export_dependencies(rosidl_default_runtime)

ament_package()
