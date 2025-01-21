// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__rosidl_typesupport_introspection_c.h"
#include "promoc_assembly_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__functions.h"
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  promoc_assembly_interfaces__msg__XBotInfo__init(message_memory);
}

void promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_fini_function(void * message_memory)
{
  promoc_assembly_interfaces__msg__XBotInfo__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_message_member_array[6] = {
  {
    "x_pos",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__msg__XBotInfo, x_pos),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "y_pos",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__msg__XBotInfo, y_pos),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "z_pos",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__msg__XBotInfo, z_pos),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "rx_pos",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__msg__XBotInfo, rx_pos),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "ry_pos",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__msg__XBotInfo, ry_pos),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "rz_pos",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__msg__XBotInfo, rz_pos),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_message_members = {
  "promoc_assembly_interfaces__msg",  // message namespace
  "XBotInfo",  // message name
  6,  // number of fields
  sizeof(promoc_assembly_interfaces__msg__XBotInfo),
  promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_message_member_array,  // message members
  promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_init_function,  // function to initialize message memory (memory has to be allocated)
  promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_message_type_support_handle = {
  0,
  &promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_promoc_assembly_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, msg, XBotInfo)() {
  if (!promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_message_type_support_handle.typesupport_identifier) {
    promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &promoc_assembly_interfaces__msg__XBotInfo__rosidl_typesupport_introspection_c__XBotInfo_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
