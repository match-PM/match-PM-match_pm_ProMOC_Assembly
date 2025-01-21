// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from promoc_assembly_interfaces:srv/LevitationXbots.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LEVITATION_XBOTS__STRUCT_H_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LEVITATION_XBOTS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in srv/LevitationXbots in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__srv__LevitationXbots_Request
{
  int32_t xbot_id;
  bool levitation;
} promoc_assembly_interfaces__srv__LevitationXbots_Request;

// Struct for a sequence of promoc_assembly_interfaces__srv__LevitationXbots_Request.
typedef struct promoc_assembly_interfaces__srv__LevitationXbots_Request__Sequence
{
  promoc_assembly_interfaces__srv__LevitationXbots_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__srv__LevitationXbots_Request__Sequence;


// Constants defined in the message

/// Struct defined in srv/LevitationXbots in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__srv__LevitationXbots_Response
{
  bool levitation;
} promoc_assembly_interfaces__srv__LevitationXbots_Response;

// Struct for a sequence of promoc_assembly_interfaces__srv__LevitationXbots_Response.
typedef struct promoc_assembly_interfaces__srv__LevitationXbots_Response__Sequence
{
  promoc_assembly_interfaces__srv__LevitationXbots_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__srv__LevitationXbots_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LEVITATION_XBOTS__STRUCT_H_
