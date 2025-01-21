// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from promoc_assembly_interfaces:srv/ArcMotion.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__TRAITS_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "promoc_assembly_interfaces/srv/detail/arc_motion__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace promoc_assembly_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const ArcMotion_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: xbot_id
  {
    out << "xbot_id: ";
    rosidl_generator_traits::value_to_yaml(msg.xbot_id, out);
    out << ", ";
  }

  // member: arc_mode
  {
    out << "arc_mode: ";
    rosidl_generator_traits::value_to_yaml(msg.arc_mode, out);
    out << ", ";
  }

  // member: arc_type
  {
    out << "arc_type: ";
    rosidl_generator_traits::value_to_yaml(msg.arc_type, out);
    out << ", ";
  }

  // member: arc_dir
  {
    out << "arc_dir: ";
    rosidl_generator_traits::value_to_yaml(msg.arc_dir, out);
    out << ", ";
  }

  // member: postion_mode
  {
    out << "postion_mode: ";
    rosidl_generator_traits::value_to_yaml(msg.postion_mode, out);
    out << ", ";
  }

  // member: x_pos
  {
    out << "x_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.x_pos, out);
    out << ", ";
  }

  // member: y_pos
  {
    out << "y_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.y_pos, out);
    out << ", ";
  }

  // member: final_speed
  {
    out << "final_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.final_speed, out);
    out << ", ";
  }

  // member: xy_max_speed
  {
    out << "xy_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.xy_max_speed, out);
    out << ", ";
  }

  // member: xy_max_accl
  {
    out << "xy_max_accl: ";
    rosidl_generator_traits::value_to_yaml(msg.xy_max_accl, out);
    out << ", ";
  }

  // member: radius_meters
  {
    out << "radius_meters: ";
    rosidl_generator_traits::value_to_yaml(msg.radius_meters, out);
    out << ", ";
  }

  // member: angle_radians
  {
    out << "angle_radians: ";
    rosidl_generator_traits::value_to_yaml(msg.angle_radians, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const ArcMotion_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: xbot_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "xbot_id: ";
    rosidl_generator_traits::value_to_yaml(msg.xbot_id, out);
    out << "\n";
  }

  // member: arc_mode
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "arc_mode: ";
    rosidl_generator_traits::value_to_yaml(msg.arc_mode, out);
    out << "\n";
  }

  // member: arc_type
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "arc_type: ";
    rosidl_generator_traits::value_to_yaml(msg.arc_type, out);
    out << "\n";
  }

  // member: arc_dir
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "arc_dir: ";
    rosidl_generator_traits::value_to_yaml(msg.arc_dir, out);
    out << "\n";
  }

  // member: postion_mode
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "postion_mode: ";
    rosidl_generator_traits::value_to_yaml(msg.postion_mode, out);
    out << "\n";
  }

  // member: x_pos
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "x_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.x_pos, out);
    out << "\n";
  }

  // member: y_pos
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "y_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.y_pos, out);
    out << "\n";
  }

  // member: final_speed
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "final_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.final_speed, out);
    out << "\n";
  }

  // member: xy_max_speed
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "xy_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.xy_max_speed, out);
    out << "\n";
  }

  // member: xy_max_accl
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "xy_max_accl: ";
    rosidl_generator_traits::value_to_yaml(msg.xy_max_accl, out);
    out << "\n";
  }

  // member: radius_meters
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "radius_meters: ";
    rosidl_generator_traits::value_to_yaml(msg.radius_meters, out);
    out << "\n";
  }

  // member: angle_radians
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "angle_radians: ";
    rosidl_generator_traits::value_to_yaml(msg.angle_radians, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const ArcMotion_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace promoc_assembly_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use promoc_assembly_interfaces::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const promoc_assembly_interfaces::srv::ArcMotion_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
{
  return promoc_assembly_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::ArcMotion_Request>()
{
  return "promoc_assembly_interfaces::srv::ArcMotion_Request";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::ArcMotion_Request>()
{
  return "promoc_assembly_interfaces/srv/ArcMotion_Request";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::ArcMotion_Request>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::ArcMotion_Request>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::srv::ArcMotion_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace promoc_assembly_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const ArcMotion_Response & msg,
  std::ostream & out)
{
  (void)msg;
  out << "null";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const ArcMotion_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  (void)msg;
  (void)indentation;
  out << "null\n";
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const ArcMotion_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace promoc_assembly_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use promoc_assembly_interfaces::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const promoc_assembly_interfaces::srv::ArcMotion_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::srv::ArcMotion_Response & msg)
{
  return promoc_assembly_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::ArcMotion_Response>()
{
  return "promoc_assembly_interfaces::srv::ArcMotion_Response";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::ArcMotion_Response>()
{
  return "promoc_assembly_interfaces/srv/ArcMotion_Response";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::ArcMotion_Response>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::ArcMotion_Response>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::srv::ArcMotion_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::ArcMotion>()
{
  return "promoc_assembly_interfaces::srv::ArcMotion";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::ArcMotion>()
{
  return "promoc_assembly_interfaces/srv/ArcMotion";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::ArcMotion>
  : std::integral_constant<
    bool,
    has_fixed_size<promoc_assembly_interfaces::srv::ArcMotion_Request>::value &&
    has_fixed_size<promoc_assembly_interfaces::srv::ArcMotion_Response>::value
  >
{
};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::ArcMotion>
  : std::integral_constant<
    bool,
    has_bounded_size<promoc_assembly_interfaces::srv::ArcMotion_Request>::value &&
    has_bounded_size<promoc_assembly_interfaces::srv::ArcMotion_Response>::value
  >
{
};

template<>
struct is_service<promoc_assembly_interfaces::srv::ArcMotion>
  : std::true_type
{
};

template<>
struct is_service_request<promoc_assembly_interfaces::srv::ArcMotion_Request>
  : std::true_type
{
};

template<>
struct is_service_response<promoc_assembly_interfaces::srv::ArcMotion_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__TRAITS_HPP_
