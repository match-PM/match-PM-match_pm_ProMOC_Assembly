cmake_minimum_required(VERSION 3.8)
project(match-PM-match_pm_ProMOC_Assembly)

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

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/XBotInfo.msg"
  "srv/SixDofMotion.srv"
  "srv/LinearMotionSi.srv"
  "srv/ActivateXbots.srv"
  "srv/LevitationXbots.srv"
  
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
