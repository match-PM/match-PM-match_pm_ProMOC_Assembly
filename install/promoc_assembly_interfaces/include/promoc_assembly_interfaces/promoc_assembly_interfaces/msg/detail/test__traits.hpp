// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from promoc_assembly_interfaces:msg/Test.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__TRAITS_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "promoc_assembly_interfaces/msg/detail/test__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace promoc_assembly_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const Test & msg,
  std::ostream & out)
{
  out << "{";
  // member: message
  {
    out << "message: ";
    rosidl_generator_traits::value_to_yaml(msg.message, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Test & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: message
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "message: ";
    rosidl_generator_traits::value_to_yaml(msg.message, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Test & msg, bool use_flow_style = false)
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
  const promoc_assembly_interfaces::msg::Test & msg,
  std::ostream & out, size_t indentation = 0)
{
  promoc_assembly_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use promoc_assembly_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const promoc_assembly_interfaces::msg::Test & msg)
{
  return promoc_assembly_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<promoc_assembly_interfaces::msg::Test>()
{
  return "promoc_assembly_interfaces::msg::Test";
}

template<>
inline const char * name<promoc_assembly_interfaces::msg::Test>()
{
  return "promoc_assembly_interfaces/msg/Test";
}

template<>
struct has_fixed_size<promoc_assembly_interfaces::msg::Test>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<promoc_assembly_interfaces::msg::Test>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<promoc_assembly_interfaces::msg::Test>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__TRAITS_HPP_
