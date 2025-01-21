cmake_minimum_required(VERSION 3.8)
project(promoc_assembly_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)


rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/test/Test.msg"
  "msg/planar_motor/XBotInfo.msg"
  "srv/planar_motor/ActivateXbots.srv"
  "srv/planar_motor/LevitationXbots.srv"
  "srv/planar_motor/LinearMotionSi.srv"
  "srv/planar_motor/SixDofMotion.srv"
  "srv/planar_motor/ArcMotionTargetRadius.srv"
  "srv/planar_motor/StopMotion.srv"
  "srv/planar_motor/RotaryMotion.srv"

)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
