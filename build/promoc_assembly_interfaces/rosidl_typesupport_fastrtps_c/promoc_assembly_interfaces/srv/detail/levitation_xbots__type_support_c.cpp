// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from promoc_assembly_interfaces:srv/LevitationXbots.idl
// generated code does not contain a copyright notice
#include "promoc_assembly_interfaces/srv/detail/levitation_xbots__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "promoc_assembly_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "promoc_assembly_interfaces/srv/detail/levitation_xbots__struct.h"
#include "promoc_assembly_interfaces/srv/detail/levitation_xbots__functions.h"
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


using _LevitationXbots_Request__ros_msg_type = promoc_assembly_interfaces__srv__LevitationXbots_Request;

static bool _LevitationXbots_Request__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _LevitationXbots_Request__ros_msg_type * ros_message = static_cast<const _LevitationXbots_Request__ros_msg_type *>(untyped_ros_message);
  // Field name: xbot_id
  {
    cdr << ros_message->xbot_id;
  }

  // Field name: levitation
  {
    cdr << (ros_message->levitation ? true : false);
  }

  return true;
}

static bool _LevitationXbots_Request__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _LevitationXbots_Request__ros_msg_type * ros_message = static_cast<_LevitationXbots_Request__ros_msg_type *>(untyped_ros_message);
  // Field name: xbot_id
  {
    cdr >> ros_message->xbot_id;
  }

  // Field name: levitation
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message->levitation = tmp ? true : false;
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_promoc_assembly_interfaces
size_t get_serialized_size_promoc_assembly_interfaces__srv__LevitationXbots_Request(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _LevitationXbots_Request__ros_msg_type * ros_message = static_cast<const _LevitationXbots_Request__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name xbot_id
  {
    size_t item_size = sizeof(ros_message->xbot_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name levitation
  {
    size_t item_size = sizeof(ros_message->levitation);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _LevitationXbots_Request__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_promoc_assembly_interfaces__srv__LevitationXbots_Request(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_promoc_assembly_interfaces
size_t max_serialized_size_promoc_assembly_interfaces__srv__LevitationXbots_Request(
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

  // member: xbot_id
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }
  // member: levitation
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = promoc_assembly_interfaces__srv__LevitationXbots_Request;
    is_plain =
      (
      offsetof(DataType, levitation) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _LevitationXbots_Request__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_promoc_assembly_interfaces__srv__LevitationXbots_Request(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_LevitationXbots_Request = {
  "promoc_assembly_interfaces::srv",
  "LevitationXbots_Request",
  _LevitationXbots_Request__cdr_serialize,
  _LevitationXbots_Request__cdr_deserialize,
  _LevitationXbots_Request__get_serialized_size,
  _LevitationXbots_Request__max_serialized_size
};

static rosidl_message_type_support_t _LevitationXbots_Request__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_LevitationXbots_Request,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, promoc_assembly_interfaces, srv, LevitationXbots_Request)() {
  return &_LevitationXbots_Request__type_support;
}

#if defined(__cplusplus)
}
#endif

// already included above
// #include <cassert>
// already included above
// #include <limits>
// already included above
// #include <string>
// already included above
// #include "rosidl_typesupport_fastrtps_c/identifier.h"
// already included above
// #include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
// already included above
// #include "promoc_assembly_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/levitation_xbots__struct.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/levitation_xbots__functions.h"
// already included above
// #include "fastcdr/Cdr.h"

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


using _LevitationXbots_Response__ros_msg_type = promoc_assembly_interfaces__srv__LevitationXbots_Response;

static bool _LevitationXbots_Response__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _LevitationXbots_Response__ros_msg_type * ros_message = static_cast<const _LevitationXbots_Response__ros_msg_type *>(untyped_ros_message);
  // Field name: levitation
  {
    cdr << (ros_message->levitation ? true : false);
  }

  return true;
}

static bool _LevitationXbots_Response__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _LevitationXbots_Response__ros_msg_type * ros_message = static_cast<_LevitationXbots_Response__ros_msg_type *>(untyped_ros_message);
  // Field name: levitation
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message->levitation = tmp ? true : false;
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_promoc_assembly_interfaces
size_t get_serialized_size_promoc_assembly_interfaces__srv__LevitationXbots_Response(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _LevitationXbots_Response__ros_msg_type * ros_message = static_cast<const _LevitationXbots_Response__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name levitation
  {
    size_t item_size = sizeof(ros_message->levitation);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _LevitationXbots_Response__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_promoc_assembly_interfaces__srv__LevitationXbots_Response(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_promoc_assembly_interfaces
size_t max_serialized_size_promoc_assembly_interfaces__srv__LevitationXbots_Response(
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

  // member: levitation
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = promoc_assembly_interfaces__srv__LevitationXbots_Response;
    is_plain =
      (
      offsetof(DataType, levitation) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _LevitationXbots_Response__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_promoc_assembly_interfaces__srv__LevitationXbots_Response(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_LevitationXbots_Response = {
  "promoc_assembly_interfaces::srv",
  "LevitationXbots_Response",
  _LevitationXbots_Response__cdr_serialize,
  _LevitationXbots_Response__cdr_deserialize,
  _LevitationXbots_Response__get_serialized_size,
  _LevitationXbots_Response__max_serialized_size
};

static rosidl_message_type_support_t _LevitationXbots_Response__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_LevitationXbots_Response,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, promoc_assembly_interfaces, srv, LevitationXbots_Response)() {
  return &_LevitationXbots_Response__type_support;
}

#if defined(__cplusplus)
}
#endif

#include "rosidl_typesupport_fastrtps_cpp/service_type_support.h"
#include "rosidl_typesupport_cpp/service_type_support.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_c/identifier.h"
// already included above
// #include "promoc_assembly_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "promoc_assembly_interfaces/srv/levitation_xbots.h"

#if defined(__cplusplus)
extern "C"
{
#endif

static service_type_support_callbacks_t LevitationXbots__callbacks = {
  "promoc_assembly_interfaces::srv",
  "LevitationXbots",
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, promoc_assembly_interfaces, srv, LevitationXbots_Request)(),
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, promoc_assembly_interfaces, srv, LevitationXbots_Response)(),
};

static rosidl_service_type_support_t LevitationXbots__handle = {
  rosidl_typesupport_fastrtps_c__identifier,
  &LevitationXbots__callbacks,
  get_service_typesupport_handle_function,
};

const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, promoc_assembly_interfaces, srv, LevitationXbots)() {
  return &LevitationXbots__handle;
}

#if defined(__cplusplus)
}
#endif
