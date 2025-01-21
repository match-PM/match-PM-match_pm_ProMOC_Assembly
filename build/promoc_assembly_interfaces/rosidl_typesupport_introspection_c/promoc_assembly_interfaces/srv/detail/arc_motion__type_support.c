// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from promoc_assembly_interfaces:srv/ArcMotion.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "promoc_assembly_interfaces/srv/detail/arc_motion__rosidl_typesupport_introspection_c.h"
#include "promoc_assembly_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "promoc_assembly_interfaces/srv/detail/arc_motion__functions.h"
#include "promoc_assembly_interfaces/srv/detail/arc_motion__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  promoc_assembly_interfaces__srv__ArcMotion_Request__init(message_memory);
}

void promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_fini_function(void * message_memory)
{
  promoc_assembly_interfaces__srv__ArcMotion_Request__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_message_member_array[12] = {
  {
    "xbot_id",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, xbot_id),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "arc_mode",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, arc_mode),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "arc_type",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, arc_type),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "arc_dir",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, arc_dir),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "postion_mode",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, postion_mode),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "x_pos",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, x_pos),  // bytes offset in struct
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
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, y_pos),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "final_speed",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, final_speed),  // bytes offset in struct
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
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, xy_max_speed),  // bytes offset in struct
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
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, xy_max_accl),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "radius_meters",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, radius_meters),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "angle_radians",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Request, angle_radians),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_message_members = {
  "promoc_assembly_interfaces__srv",  // message namespace
  "ArcMotion_Request",  // message name
  12,  // number of fields
  sizeof(promoc_assembly_interfaces__srv__ArcMotion_Request),
  promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_message_member_array,  // message members
  promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_message_type_support_handle = {
  0,
  &promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_promoc_assembly_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, ArcMotion_Request)() {
  if (!promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_message_type_support_handle.typesupport_identifier) {
    promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &promoc_assembly_interfaces__srv__ArcMotion_Request__rosidl_typesupport_introspection_c__ArcMotion_Request_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

// already included above
// #include <stddef.h>
// already included above
// #include "promoc_assembly_interfaces/srv/detail/arc_motion__rosidl_typesupport_introspection_c.h"
// already included above
// #include "promoc_assembly_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "rosidl_typesupport_introspection_c/field_types.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
// already included above
// #include "rosidl_typesupport_introspection_c/message_introspection.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/arc_motion__functions.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/arc_motion__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  promoc_assembly_interfaces__srv__ArcMotion_Response__init(message_memory);
}

void promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_fini_function(void * message_memory)
{
  promoc_assembly_interfaces__srv__ArcMotion_Response__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_message_member_array[1] = {
  {
    "structure_needs_at_least_one_member",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_UINT8,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces__srv__ArcMotion_Response, structure_needs_at_least_one_member),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_message_members = {
  "promoc_assembly_interfaces__srv",  // message namespace
  "ArcMotion_Response",  // message name
  1,  // number of fields
  sizeof(promoc_assembly_interfaces__srv__ArcMotion_Response),
  promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_message_member_array,  // message members
  promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_message_type_support_handle = {
  0,
  &promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_promoc_assembly_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, ArcMotion_Response)() {
  if (!promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_message_type_support_handle.typesupport_identifier) {
    promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &promoc_assembly_interfaces__srv__ArcMotion_Response__rosidl_typesupport_introspection_c__ArcMotion_Response_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "promoc_assembly_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/arc_motion__rosidl_typesupport_introspection_c.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/service_introspection.h"

// this is intentionally not const to allow initialization later to prevent an initialization race
static rosidl_typesupport_introspection_c__ServiceMembers promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_service_members = {
  "promoc_assembly_interfaces__srv",  // service namespace
  "ArcMotion",  // service name
  // these two fields are initialized below on the first access
  NULL,  // request message
  // promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_Request_message_type_support_handle,
  NULL  // response message
  // promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_Response_message_type_support_handle
};

static rosidl_service_type_support_t promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_service_type_support_handle = {
  0,
  &promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_service_members,
  get_service_typesupport_handle_function,
};

// Forward declaration of request/response type support functions
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, ArcMotion_Request)();

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, ArcMotion_Response)();

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_promoc_assembly_interfaces
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, ArcMotion)() {
  if (!promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_service_type_support_handle.typesupport_identifier) {
    promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_service_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  rosidl_typesupport_introspection_c__ServiceMembers * service_members =
    (rosidl_typesupport_introspection_c__ServiceMembers *)promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_service_type_support_handle.data;

  if (!service_members->request_members_) {
    service_members->request_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, ArcMotion_Request)()->data;
  }
  if (!service_members->response_members_) {
    service_members->response_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, promoc_assembly_interfaces, srv, ArcMotion_Response)()->data;
  }

  return &promoc_assembly_interfaces__srv__detail__arc_motion__rosidl_typesupport_introspection_c__ArcMotion_service_type_support_handle;
}
