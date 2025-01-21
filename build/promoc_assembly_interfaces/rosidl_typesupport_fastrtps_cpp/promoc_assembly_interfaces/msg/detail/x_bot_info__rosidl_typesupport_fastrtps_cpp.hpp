// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__rosidl_typesupport_fastrtps_cpp.hpp.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_

#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_interface/macros.h"
#include "promoc_assembly_interfaces/msg/rosidl_typesupport_fastrtps_cpp__visibility_control.h"
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__struct.hpp"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

#include "fastcdr/Cdr.h"

namespace promoc_assembly_interfaces
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
cdr_serialize(
  const promoc_assembly_interfaces::msg::XBotInfo & ros_message,
  eprosima::fastcdr::Cdr & cdr);

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  promoc_assembly_interfaces::msg::XBotInfo & ros_message);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
get_serialized_size(
  const promoc_assembly_interfaces::msg::XBotInfo & ros_message,
  size_t current_alignment);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
max_serialized_size_XBotInfo(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace promoc_assembly_interfaces

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, promoc_assembly_interfaces, msg, XBotInfo)();

#ifdef __cplusplus
}
#endif

#endif  // PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
