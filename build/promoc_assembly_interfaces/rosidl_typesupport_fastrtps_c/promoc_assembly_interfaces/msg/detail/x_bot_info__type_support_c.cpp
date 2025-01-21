// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "promoc_assembly_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__struct.h"
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__functions.h"
#include "fastcdr/Cdr.h"

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

// includes and forward declarations of message dependencies and their conversion functions

#if defined(__cplusplus)
extern "C"
{
#endif


// forward declare type support functions


using _XBotInfo__ros_msg_type = promoc_assembly_interfaces__msg__XBotInfo;

static bool _XBotInfo__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _XBotInfo__ros_msg_type * ros_message = static_cast<const _XBotInfo__ros_msg_type *>(untyped_ros_message);
  // Field name: x_pos
  {
    cdr << ros_message->x_pos;
  }

  // Field name: y_pos
  {
    cdr << ros_message->y_pos;
  }

  // Field name: z_pos
  {
    cdr << ros_message->z_pos;
  }

  // Field name: rx_pos
  {
    cdr << ros_message->rx_pos;
  }

  // Field name: ry_pos
  {
    cdr << ros_message->ry_pos;
  }

  // Field name: rz_pos
  {
    cdr << ros_message->rz_pos;
  }

  return true;
}

static bool _XBotInfo__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _XBotInfo__ros_msg_type * ros_message = static_cast<_XBotInfo__ros_msg_type *>(untyped_ros_message);
  // Field name: x_pos
  {
    cdr >> ros_message->x_pos;
  }

  // Field name: y_pos
  {
    cdr >> ros_message->y_pos;
  }

  // Field name: z_pos
  {
    cdr >> ros_message->z_pos;
  }

  // Field name: rx_pos
  {
    cdr >> ros_message->rx_pos;
  }

  // Field name: ry_pos
  {
    cdr >> ros_message->ry_pos;
  }

  // Field name: rz_pos
  {
    cdr >> ros_message->rz_pos;
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_promoc_assembly_interfaces
size_t get_serialized_size_promoc_assembly_interfaces__msg__XBotInfo(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _XBotInfo__ros_msg_type * ros_message = static_cast<const _XBotInfo__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name x_pos
  {
    size_t item_size = sizeof(ros_message->x_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name y_pos
  {
    size_t item_size = sizeof(ros_message->y_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name z_pos
  {
    size_t item_size = sizeof(ros_message->z_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name rx_pos
  {
    size_t item_size = sizeof(ros_message->rx_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name ry_pos
  {
    size_t item_size = sizeof(ros_message->ry_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name rz_pos
  {
    size_t item_size = sizeof(ros_message->rz_pos);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _XBotInfo__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_promoc_assembly_interfaces__msg__XBotInfo(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_promoc_assembly_interfaces
size_t max_serialized_size_promoc_assembly_interfaces__msg__XBotInfo(
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

  // member: x_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: y_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: z_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: rx_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: ry_pos
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: rz_pos
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
    using DataType = promoc_assembly_interfaces__msg__XBotInfo;
    is_plain =
      (
      offsetof(DataType, rz_pos) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _XBotInfo__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_promoc_assembly_interfaces__msg__XBotInfo(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_XBotInfo = {
  "promoc_assembly_interfaces::msg",
  "XBotInfo",
  _XBotInfo__cdr_serialize,
  _XBotInfo__cdr_deserialize,
  _XBotInfo__get_serialized_size,
  _XBotInfo__max_serialized_size
};

static rosidl_message_type_support_t _XBotInfo__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_XBotInfo,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, promoc_assembly_interfaces, msg, XBotInfo)() {
  return &_XBotInfo__type_support;
}

#if defined(__cplusplus)
}
#endif
