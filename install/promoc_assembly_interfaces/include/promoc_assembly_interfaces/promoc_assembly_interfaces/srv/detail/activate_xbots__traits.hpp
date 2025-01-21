// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from promoc_assembly_interfaces:srv/ActivateXbots.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__TRAITS_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "promoc_assembly_interfaces/srv/detail/activate_xbots__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace promoc_assembly_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const ActivateXbots_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: xbot_id
  {
    out << "xbot_id: ";
    rosidl_generator_traits::value_to_yaml(msg.xbot_id, out);
    out << ", ";
  }

  // member: activation_status
  {
    out << "activation_status: ";
    rosidl_generator_traits::value_to_yaml(msg.activation_status, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const ActivateXbots_Request & msg,
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

  // member: activation_status
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "activation_status: ";
    rosidl_generator_traits::value_to_yaml(msg.activation_status, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const ActivateXbots_Request & msg, bool use_flow_style = false)
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
  const promoc_assembly_interfaces::srv::ActivateXbots_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::srv::ActivateXbots_Request & msg)
{
  return promoc_assembly_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::ActivateXbots_Request>()
{
  return "promoc_assembly_interfaces::srv::ActivateXbots_Request";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::ActivateXbots_Request>()
{
  return "promoc_assembly_interfaces/srv/ActivateXbots_Request";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::ActivateXbots_Request>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::ActivateXbots_Request>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::srv::ActivateXbots_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace promoc_assembly_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const ActivateXbots_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: activation_status
  {
    out << "activation_status: ";
    rosidl_generator_traits::value_to_yaml(msg.activation_status, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const ActivateXbots_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: activation_status
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "activation_status: ";
    rosidl_generator_traits::value_to_yaml(msg.activation_status, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const ActivateXbots_Response & msg, bool use_flow_style = false)
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
  const promoc_assembly_interfaces::srv::ActivateXbots_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::srv::ActivateXbots_Response & msg)
{
  return promoc_assembly_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::ActivateXbots_Response>()
{
  return "promoc_assembly_interfaces::srv::ActivateXbots_Response";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::ActivateXbots_Response>()
{
  return "promoc_assembly_interfaces/srv/ActivateXbots_Response";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::ActivateXbots_Response>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::ActivateXbots_Response>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::srv::ActivateXbots_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<promoc_assembly_interfaces::srv::ActivateXbots>()
{
  return "promoc_assembly_interfaces::srv::ActivateXbots";
}

template<>
inline const char * name<promoc_assembly_interfaces::srv::ActivateXbots>()
{
  return "promoc_assembly_interfaces/srv/ActivateXbots";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::srv::ActivateXbots>
  : std::integral_constant<
    bool,
    has_fixed_size<promoc_assembly_interfaces::srv::ActivateXbots_Request>::value &&
    has_fixed_size<promoc_assembly_interfaces::srv::ActivateXbots_Response>::value
  >
{
};

template<>
struct has_bounded_size<promoc_assembly_interfaces::srv::ActivateXbots>
  : std::integral_constant<
    bool,
    has_bounded_size<promoc_assembly_interfaces::srv::ActivateXbots_Request>::value &&
    has_bounded_size<promoc_assembly_interfaces::srv::ActivateXbots_Response>::value
  >
{
};

template<>
struct is_service<promoc_assembly_interfaces::srv::ActivateXbots>
  : std::true_type
{
};

template<>
struct is_service_request<promoc_assembly_interfaces::srv::ActivateXbots_Request>
  : std::true_type
{
};

template<>
struct is_service_response<promoc_assembly_interfaces::srv::ActivateXbots_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__TRAITS_HPP_
