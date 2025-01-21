// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from promoc_assembly_interfaces:srv/SixDofMotion.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__TRAITS_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "promoc_assembly_interfaces/srv/detail/six_dof_motion__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace promoc_assembly_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const SixDofMotion_Request & msg,
  std::ostream & out)
{
  out << "{";
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

  // member: z_pos
  {
    out << "z_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.z_pos, out);
    out << ", ";
  }

  // member: rx_pos
  {
    out << "rx_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.rx_pos, out);
    out << ", ";
  }

  // member: ry_pos
  {
    out << "ry_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.ry_pos, out);
    out << ", ";
  }

  // member: rz_pos
  {
    out << "rz_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.rz_pos, out);
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

  // member: z_max_speed
  {
    out << "z_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.z_max_speed, out);
    out << ", ";
  }

  // member: rx_max_speed
  {
    out << "rx_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.rx_max_speed, out);
    out << ", ";
  }

  // member: ry_max_speed
  {
    out << "ry_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.ry_max_speed, out);
    out << ", ";
  }

  // member: rz_max_speed
  {
    out << "rz_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.rz_max_speed, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const SixDofMotion_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
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

  // member: z_pos
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "z_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.z_pos, out);
    out << "\n";
  }

  // member: rx_pos
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "rx_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.rx_pos, out);
    out << "\n";
  }

  // member: ry_pos
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "ry_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.ry_pos, out);
    out << "\n";
  }

  // member: rz_pos
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "rz_pos: ";
    rosidl_generator_traits::value_to_yaml(msg.rz_pos, out);
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

  // member: z_max_speed
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "z_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.z_max_speed, out);
    out << "\n";
  }

  // member: rx_max_speed
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "rx_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.rx_max_speed, out);
    out << "\n";
  }

  // member: ry_max_speed
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "ry_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.ry_max_speed, out);
    out << "\n";
  }

  // member: rz_max_speed
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "rz_max_speed: ";
    rosidl_generator_traits::value_to_yaml(msg.rz_max_speed, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SixDofMotion_Request & msg, bool use_flow_style = false)
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
  const promoc_assembly_interfaces::srv::SixDofMotion_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
{
  return promoc_assembly_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::SixDofMotion_Request>()
{
  return "promoc_assembly_interfaces::srv::SixDofMotion_Request";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::SixDofMotion_Request>()
{
  return "promoc_assembly_interfaces/srv/SixDofMotion_Request";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::SixDofMotion_Request>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::SixDofMotion_Request>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::srv::SixDofMotion_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace promoc_assembly_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const SixDofMotion_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: finished
  {
    out << "finished: ";
    rosidl_generator_traits::value_to_yaml(msg.finished, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const SixDofMotion_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: finished
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "finished: ";
    rosidl_generator_traits::value_to_yaml(msg.finished, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SixDofMotion_Response & msg, bool use_flow_style = false)
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
  const promoc_assembly_interfaces::srv::SixDofMotion_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::srv::SixDofMotion_Response & msg)
{
  return promoc_assembly_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::SixDofMotion_Response>()
{
  return "promoc_assembly_interfaces::srv::SixDofMotion_Response";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::SixDofMotion_Response>()
{
  return "promoc_assembly_interfaces/srv/SixDofMotion_Response";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::SixDofMotion_Response>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::SixDofMotion_Response>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::srv::SixDofMotion_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::SixDofMotion>()
{
  return "promoc_assembly_interfaces::srv::SixDofMotion";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::SixDofMotion>()
{
  return "promoc_assembly_interfaces/srv/SixDofMotion";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::SixDofMotion>
  : std::integral_constant<
    bool,
    has_fixed_size<promoc_assembly_interfaces::srv::SixDofMotion_Request>::value &&
    has_fixed_size<promoc_assembly_interfaces::srv::SixDofMotion_Response>::value
  >
{
};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::SixDofMotion>
  : std::integral_constant<
    bool,
    has_bounded_size<promoc_assembly_interfaces::srv::SixDofMotion_Request>::value &&
    has_bounded_size<promoc_assembly_interfaces::srv::SixDofMotion_Response>::value
  >
{
};

template<>
struct is_service<promoc_assembly_interfaces::srv::SixDofMotion>
  : std::true_type
{
};

template<>
struct is_service_request<promoc_assembly_interfaces::srv::SixDofMotion_Request>
  : std::true_type
{
};

template<>
struct is_service_response<promoc_assembly_interfaces::srv::SixDofMotion_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__TRAITS_HPP_
