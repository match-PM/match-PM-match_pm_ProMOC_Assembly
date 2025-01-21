// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from promoc_assembly_interfaces:srv/ActivateXbots.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__STRUCT_H_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in srv/ActivateXbots in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__srv__ActivateXbots_Request
{
  int32_t xbot_id;
  bool activation_status;
} promoc_assembly_interfaces__srv__ActivateXbots_Request;

// Struct for a sequence of promoc_assembly_interfaces__srv__ActivateXbots_Request.
typedef struct promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence
{
  promoc_assembly_interfaces__srv__ActivateXbots_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence;


// Constants defined in the message

/// Struct defined in srv/ActivateXbots in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__srv__ActivateXbots_Response
{
  bool activation_status;
} promoc_assembly_interfaces__srv__ActivateXbots_Response;

// Struct for a sequence of promoc_assembly_interfaces__srv__ActivateXbots_Response.
typedef struct promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence
{
  promoc_assembly_interfaces__srv__ActivateXbots_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__STRUCT_H_
