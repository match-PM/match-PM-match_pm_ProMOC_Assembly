// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__TRAITS_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "promoc_assembly_interfaces/msg/detail/x_bot_info__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace promoc_assembly_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const XBotInfo & msg,
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
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const XBotInfo & msg,
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
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const XBotInfo & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace promoc_assembly_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use promoc_assembly_interfaces::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const promoc_assembly_interfaces::msg::XBotInfo & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::msg::XBotInfo & msg)
{
  return promoc_assembly_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::msg::XBotInfo>()
{
  return "promoc_assembly_interfaces::msg::XBotInfo";
}

template<>
inline const char * name<promoc_assembly_interfaces::msg::XBotInfo>()
{
  return "promoc_assembly_interfaces/msg/XBotInfo";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::msg::XBotInfo>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::msg::XBotInfo>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<promoc_assembly_interfaces::msg::XBotInfo>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__TRAITS_HPP_
