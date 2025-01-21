// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from promoc_assembly_interfaces:srv/LinearMotionSi.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LINEAR_MOTION_SI__TRAITS_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LINEAR_MOTION_SI__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "promoc_assembly_interfaces/srv/detail/linear_motion_si__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace promoc_assembly_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const LinearMotionSi_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: xbot_id
  {
    out << "xbot_id: ";
    rosidl_generator_traits::value_to_yaml(msg.xbot_id, out);
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
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const LinearMotionSi_Request & msg,
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
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const LinearMotionSi_Request & msg, bool use_flow_style = false)
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
  const promoc_assembly_interfaces::srv::LinearMotionSi_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::srv::LinearMotionSi_Request & msg)
{
  return promoc_assembly_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::LinearMotionSi_Request>()
{
  return "promoc_assembly_interfaces::srv::LinearMotionSi_Request";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::LinearMotionSi_Request>()
{
  return "promoc_assembly_interfaces/srv/LinearMotionSi_Request";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::LinearMotionSi_Request>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::LinearMotionSi_Request>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::srv::LinearMotionSi_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace promoc_assembly_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const LinearMotionSi_Response & msg,
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
  const LinearMotionSi_Response & msg,
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

inline std::string to_yaml(const LinearMotionSi_Response & msg, bool use_flow_style = false)
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
  const promoc_assembly_interfaces::srv::LinearMotionSi_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::srv::LinearMotionSi_Response & msg)
{
  return promoc_assembly_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::LinearMotionSi_Response>()
{
  return "promoc_assembly_interfaces::srv::LinearMotionSi_Response";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::LinearMotionSi_Response>()
{
  return "promoc_assembly_interfaces/srv/LinearMotionSi_Response";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::LinearMotionSi_Response>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::LinearMotionSi_Response>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::srv::LinearMotionSi_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::LinearMotionSi>()
{
  return "promoc_assembly_interfaces::srv::LinearMotionSi";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::LinearMotionSi>()
{
  return "promoc_assembly_interfaces/srv/LinearMotionSi";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::LinearMotionSi>
  : std::integral_constant<
    bool,
    has_fixed_size<promoc_assembly_interfaces::srv::LinearMotionSi_Request>::value &&
    has_fixed_size<promoc_assembly_interfaces::srv::LinearMotionSi_Response>::value
  >
{
};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::LinearMotionSi>
  : std::integral_constant<
    bool,
    has_bounded_size<promoc_assembly_interfaces::srv::LinearMotionSi_Request>::value &&
    has_bounded_size<promoc_assembly_interfaces::srv::LinearMotionSi_Response>::value
  >
{
};

template<>
struct is_service<promoc_assembly_interfaces::srv::LinearMotionSi>
  : std::true_type
{
};

template<>
struct is_service_request<promoc_assembly_interfaces::srv::LinearMotionSi_Request>
  : std::true_type
{
};

template<>
struct is_service_response<promoc_assembly_interfaces::srv::LinearMotionSi_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LINEAR_MOTION_SI__TRAITS_HPP_
