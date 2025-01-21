// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from promoc_assembly_interfaces:srv/SixDofMotion.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "promoc_assembly_interfaces/srv/detail/six_dof_motion__rosidl_typesupport_introspection_c.h"
#include "promoc_assembly_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "promoc_assembly_interfaces/srv/detail/six_dof_motion__functions.h"
#include "promoc_assembly_interfaces/srv/detail/six_dof_motion__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  promoc_assembly_interfaces__srv__SixDofMotion_Request__init(message_memory);
}

void promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_fini_function(void * message_memory)
{
  promoc_assembly_interfaces__srv__SixDofMotion_Request__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_member_array[12] = {
  {
    "x_pos",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, x_pos),  // bytes offset in struct
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
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, y_pos),  // bytes offset in struct
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
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, z_pos),  // bytes offset in struct
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
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, rx_pos),  // bytes offset in struct
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
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, ry_pos),  // bytes offset in struct
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
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, rz_pos),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "xy_max_speed",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, xy_max_speed),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "xy_max_accl",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, xy_max_accl),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "z_max_speed",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, z_max_speed),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "rx_max_speed",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, rx_max_speed),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "ry_max_speed",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, ry_max_speed),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "rz_max_speed",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Request, rz_max_speed),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_members = {
  "promoc_assembly_interfaces__srv",  // message namespace
  "SixDofMotion_Request",  // message name
  12,  // number of fields
  sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Request),
  promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_member_array,  // message members
  promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_type_support_handle = {
  0,
  &promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_promoc_assembly_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, SixDofMotion_Request)() {
  if (!promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_type_support_handle.typesupport_identifier) {
    promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &promoc_assembly_interfaces__srv__SixDofMotion_Request__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

// already included above
// #include <stddef.h>
// already included above
// #include "promoc_assembly_interfaces/srv/detail/six_dof_motion__rosidl_typesupport_introspection_c.h"
// already included above
// #include "promoc_assembly_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "rosidl_typesupport_introspection_c/field_types.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
// already included above
// #include "rosidl_typesupport_introspection_c/message_introspection.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/six_dof_motion__functions.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/six_dof_motion__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  promoc_assembly_interfaces__srv__SixDofMotion_Response__init(message_memory);
}

void promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_fini_function(void * message_memory)
{
  promoc_assembly_interfaces__srv__SixDofMotion_Response__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_member_array[1] = {
  {
    "finished",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__SixDofMotion_Response, finished),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_members = {
  "promoc_assembly_interfaces__srv",  // message namespace
  "SixDofMotion_Response",  // message name
  1,  // number of fields
  sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Response),
  promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_member_array,  // message members
  promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_type_support_handle = {
  0,
  &promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_promoc_assembly_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, SixDofMotion_Response)() {
  if (!promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_type_support_handle.typesupport_identifier) {
    promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &promoc_assembly_interfaces__srv__SixDofMotion_Response__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "promoc_assembly_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/six_dof_motion__rosidl_typesupport_introspection_c.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/service_introspection.h"

// this is intentionally not const to allow initialization later to prevent an initialization race
static rosidl_typesupport_introspection_c__ServiceMembers promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_service_members = {
  "promoc_assembly_interfaces__srv",  // service namespace
  "SixDofMotion",  // service name
  // these two fields are initialized below on the first access
  NULL,  // request message
  // promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_Request_message_type_support_handle,
  NULL  // response message
  // promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_Response_message_type_support_handle
};

static rosidl_service_type_support_t promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_service_type_support_handle = {
  0,
  &promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_service_members,
  get_service_typesupport_handle_function,
};

// Forward declaration of request/response type support functions
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, SixDofMotion_Request)();

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, SixDofMotion_Response)();

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_promoc_assembly_interfaces
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, SixDofMotion)() {
  if (!promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_service_type_support_handle.typesupport_identifier) {
    promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_service_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  rosidl_typesupport_introspection_c__ServiceMembers * service_members =
    (rosidl_typesupport_introspection_c__ServiceMembers *)promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_service_type_support_handle.data;

  if (!service_members->request_members_) {
    service_members->request_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, SixDofMotion_Request)()->data;
  }
  if (!service_members->response_members_) {
    service_members->response_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, SixDofMotion_Response)()->data;
  }

  return &promoc_assembly_interfaces__srv__detail__six_dof_motion__rosidl_typesupport_introspection_c__SixDofMotion_service_type_support_handle;
}
