// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__rosidl_typesupport_fastrtps_cpp.hpp"
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__struct.hpp"

#include <limits>
#include <stdexcept>
#include <string>
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_fastrtps_cpp/wstring_conversion.hpp"
#include "fastcdr/Cdr.h"


// forward declaration of message dependencies and their conversion functions

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
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: x_pos
  cdr << ros_message.x_pos;
  // Member: y_pos
  cdr << ros_message.y_pos;
  // Member: z_pos
  cdr << ros_message.z_pos;
  // Member: rx_pos
  cdr << ros_message.rx_pos;
  // Member: ry_pos
  cdr << ros_message.ry_pos;
  // Member: rz_pos
  cdr << ros_message.rz_pos;
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  promoc_assembly_interfaces::msg::XBotInfo & ros_message)
{
  // Member: x_pos
  cdr >> ros_message.x_pos;

  // Member: y_pos
  cdr >> ros_message.y_pos;

  // Member: z_pos
  cdr >> ros_message.z_pos;

  // Member: rx_pos
  cdr >> ros_message.rx_pos;

  // Member: ry_pos
  cdr >> ros_message.ry_pos;

  // Member: rz_pos
  cdr >> ros_message.rz_pos;

  return true;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
get_serialized_size(
  const promoc_assembly_interfaces::msg::XBotInfo & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: x_pos
  {
    size_t item_size = sizeof(ros_message.x_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: y_pos
  {
    size_t item_size = sizeof(ros_message.y_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: z_pos
  {
    size_t item_size = sizeof(ros_message.z_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: rx_pos
  {
    size_t item_size = sizeof(ros_message.rx_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: ry_pos
  {
    size_t item_size = sizeof(ros_message.ry_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: rz_pos
  {
    size_t item_size = sizeof(ros_message.rz_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
max_serialized_size_XBotInfo(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;


  // Member: x_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: y_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: z_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: rx_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: ry_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: rz_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = promoc_assembly_interfaces::msg::XBotInfo;
    is_plain =
      (
      offsetof(DataType, rz_pos) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _XBotInfo__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const promoc_assembly_interfaces::msg::XBotInfo *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _XBotInfo__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<promoc_assembly_interfaces::msg::XBotInfo *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _XBotInfo__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const promoc_assembly_interfaces::msg::XBotInfo *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _XBotInfo__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_XBotInfo(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _XBotInfo__callbacks = {
  "promoc_assembly_interfaces::msg",
  "XBotInfo",
  _XBotInfo__cdr_serialize,
  _XBotInfo__cdr_deserialize,
  _XBotInfo__get_serialized_size,
  _XBotInfo__max_serialized_size
};

static rosidl_message_type_support_t _XBotInfo__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_XBotInfo__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace promoc_assembly_interfaces

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_promoc_assembly_interfaces
const rosidl_message_type_support_t *
get_message_type_support_handle<promoc_assembly_interfaces::msg::XBotInfo>()
{
  return &promoc_assembly_interfaces::msg::typesupport_fastrtps_cpp::_XBotInfo__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, promoc_assembly_interfaces, msg, XBotInfo)() {
  return &promoc_assembly_interfaces::msg::typesupport_fastrtps_cpp::_XBotInfo__handle;
}

#ifdef __cplusplus
}
#endif
