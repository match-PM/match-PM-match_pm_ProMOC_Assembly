// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from promoc_assembly_interfaces:srv/LinearMotionSi.idl
// generated code does not contain a copyright notice
#include "promoc_assembly_interfaces/srv/detail/linear_motion_si__rosidl_typesupport_fastrtps_cpp.hpp"
#include "promoc_assembly_interfaces/srv/detail/linear_motion_si__struct.hpp"

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

namespace srv
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
cdr_serialize(
  const promoc_assembly_interfaces::srv::LinearMotionSi_Request & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: xbot_id
  cdr << ros_message.xbot_id;
  // Member: x_pos
  cdr << ros_message.x_pos;
  // Member: y_pos
  cdr << ros_message.y_pos;
  // Member: xy_max_speed
  cdr << ros_message.xy_max_speed;
  // Member: xy_max_accl
  cdr << ros_message.xy_max_accl;
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  promoc_assembly_interfaces::srv::LinearMotionSi_Request & ros_message)
{
  // Member: xbot_id
  cdr >> ros_message.xbot_id;

  // Member: x_pos
  cdr >> ros_message.x_pos;

  // Member: y_pos
  cdr >> ros_message.y_pos;

  // Member: xy_max_speed
  cdr >> ros_message.xy_max_speed;

  // Member: xy_max_accl
  cdr >> ros_message.xy_max_accl;

  return true;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
get_serialized_size(
  const promoc_assembly_interfaces::srv::LinearMotionSi_Request & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: xbot_id
  {
    size_t item_size = sizeof(ros_message.xbot_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
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
  // Member: xy_max_speed
  {
    size_t item_size = sizeof(ros_message.xy_max_speed);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: xy_max_accl
  {
    size_t item_size = sizeof(ros_message.xy_max_accl);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
max_serialized_size_LinearMotionSi_Request(
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


  // Member: xbot_id
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

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

  // Member: xy_max_speed
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: xy_max_accl
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
    using DataType = promoc_assembly_interfaces::srv::LinearMotionSi_Request;
    is_plain =
      (
      offsetof(DataType, xy_max_accl) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _LinearMotionSi_Request__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const promoc_assembly_interfaces::srv::LinearMotionSi_Request *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _LinearMotionSi_Request__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<promoc_assembly_interfaces::srv::LinearMotionSi_Request *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _LinearMotionSi_Request__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const promoc_assembly_interfaces::srv::LinearMotionSi_Request *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _LinearMotionSi_Request__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_LinearMotionSi_Request(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _LinearMotionSi_Request__callbacks = {
  "promoc_assembly_interfaces::srv",
  "LinearMotionSi_Request",
  _LinearMotionSi_Request__cdr_serialize,
  _LinearMotionSi_Request__cdr_deserialize,
  _LinearMotionSi_Request__get_serialized_size,
  _LinearMotionSi_Request__max_serialized_size
};

static rosidl_message_type_support_t _LinearMotionSi_Request__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_LinearMotionSi_Request__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace srv

}  // namespace promoc_assembly_interfaces

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_promoc_assembly_interfaces
const rosidl_message_type_support_t *
get_message_type_support_handle<promoc_assembly_interfaces::srv::LinearMotionSi_Request>()
{
  return &promoc_assembly_interfaces::srv::typesupport_fastrtps_cpp::_LinearMotionSi_Request__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, promoc_assembly_interfaces, srv, LinearMotionSi_Request)() {
  return &promoc_assembly_interfaces::srv::typesupport_fastrtps_cpp::_LinearMotionSi_Request__handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include <limits>
// already included above
// #include <stdexcept>
// already included above
// #include <string>
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
// already included above
// #include "rosidl_typesupport_fastrtps_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_cpp/wstring_conversion.hpp"
// already included above
// #include "fastcdr/Cdr.h"


// forward declaration of message dependencies and their conversion functions

namespace promoc_assembly_interfaces
{

namespace srv
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
cdr_serialize(
  const promoc_assembly_interfaces::srv::LinearMotionSi_Response & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: finished
  cdr << (ros_message.finished ? true : false);
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  promoc_assembly_interfaces::srv::LinearMotionSi_Response & ros_message)
{
  // Member: finished
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message.finished = tmp ? true : false;
  }

  return true;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
get_serialized_size(
  const promoc_assembly_interfaces::srv::LinearMotionSi_Response & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: finished
  {
    size_t item_size = sizeof(ros_message.finished);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_promoc_assembly_interfaces
max_serialized_size_LinearMotionSi_Response(
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


  // Member: finished
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
    using DataType = promoc_assembly_interfaces::srv::LinearMotionSi_Response;
    is_plain =
      (
      offsetof(DataType, finished) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _LinearMotionSi_Response__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const promoc_assembly_interfaces::srv::LinearMotionSi_Response *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _LinearMotionSi_Response__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<promoc_assembly_interfaces::srv::LinearMotionSi_Response *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _LinearMotionSi_Response__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const promoc_assembly_interfaces::srv::LinearMotionSi_Response *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _LinearMotionSi_Response__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_LinearMotionSi_Response(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _LinearMotionSi_Response__callbacks = {
  "promoc_assembly_interfaces::srv",
  "LinearMotionSi_Response",
  _LinearMotionSi_Response__cdr_serialize,
  _LinearMotionSi_Response__cdr_deserialize,
  _LinearMotionSi_Response__get_serialized_size,
  _LinearMotionSi_Response__max_serialized_size
};

static rosidl_message_type_support_t _LinearMotionSi_Response__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_LinearMotionSi_Response__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace srv

}  // namespace promoc_assembly_interfaces

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_promoc_assembly_interfaces
const rosidl_message_type_support_t *
get_message_type_support_handle<promoc_assembly_interfaces::srv::LinearMotionSi_Response>()
{
  return &promoc_assembly_interfaces::srv::typesupport_fastrtps_cpp::_LinearMotionSi_Response__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, promoc_assembly_interfaces, srv, LinearMotionSi_Response)() {
  return &promoc_assembly_interfaces::srv::typesupport_fastrtps_cpp::_LinearMotionSi_Response__handle;
}

#ifdef __cplusplus
}
#endif

#include "rmw/error_handling.h"
// already included above
// #include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
#include "rosidl_typesupport_fastrtps_cpp/service_type_support.h"
#include "rosidl_typesupport_fastrtps_cpp/service_type_support_decl.hpp"

namespace promoc_assembly_interfaces
{

namespace srv
{

namespace typesupport_fastrtps_cpp
{

static service_type_support_callbacks_t _LinearMotionSi__callbacks = {
  "promoc_assembly_interfaces::srv",
  "LinearMotionSi",
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, promoc_assembly_interfaces, srv, LinearMotionSi_Request)(),
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, promoc_assembly_interfaces, srv, LinearMotionSi_Response)(),
};

static rosidl_service_type_support_t _LinearMotionSi__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_LinearMotionSi__callbacks,
  get_service_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace srv

}  // namespace promoc_assembly_interfaces

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_promoc_assembly_interfaces
const rosidl_service_type_support_t *
get_service_type_support_handle<promoc_assembly_interfaces::srv::LinearMotionSi>()
{
  return &promoc_assembly_interfaces::srv::typesupport_fastrtps_cpp::_LinearMotionSi__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, promoc_assembly_interfaces, srv, LinearMotionSi)() {
  return &promoc_assembly_interfaces::srv::typesupport_fastrtps_cpp::_LinearMotionSi__handle;
}

#ifdef __cplusplus
}
#endif
