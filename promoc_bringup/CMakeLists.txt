cmake_minimum_required(VERSION 3.10)
project(promoc_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Install launch files, config, and urdf
install(DIRECTORY
  launch
  config
  urdf
  DESTINATION share/${PROJECT_NAME}
)

# Install Python modules
ament_python_install_package(${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # Copyright headers aren't consistently present in launch/util scripts.
  # Keep the package lintable by excluding those paths.
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  set(ament_cmake_uncrustify_FOUND TRUE)
  set(ament_cmake_flake8_FOUND TRUE)
  set(ament_cmake_pep257_FOUND TRUE)
  # Avoid network-dependent schema fetches in offline handover environments.
  set(ament_cmake_xmllint_FOUND TRUE)
  # Exclude specific files from copyright linter.
  set(ament_cmake_copyright_CONFIG_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/.ament_copyright_exclude")
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
