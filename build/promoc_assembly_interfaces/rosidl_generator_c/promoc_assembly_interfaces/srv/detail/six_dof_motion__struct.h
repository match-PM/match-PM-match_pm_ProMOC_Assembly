// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from promoc_assembly_interfaces:srv/SixDofMotion.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__STRUCT_H_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in srv/SixDofMotion in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__srv__SixDofMotion_Request
{
  double x_pos;
  double y_pos;
  double z_pos;
  double rx_pos;
  double ry_pos;
  double rz_pos;
  double xy_max_speed;
  double xy_max_accl;
  double z_max_speed;
  double rx_max_speed;
  double ry_max_speed;
  double rz_max_speed;
} promoc_assembly_interfaces__srv__SixDofMotion_Request;

// Struct for a sequence of promoc_assembly_interfaces__srv__SixDofMotion_Request.
typedef struct promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence
{
  promoc_assembly_interfaces__srv__SixDofMotion_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence;


// Constants defined in the message

/// Struct defined in srv/SixDofMotion in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__srv__SixDofMotion_Response
{
  bool finished;
} promoc_assembly_interfaces__srv__SixDofMotion_Response;

// Struct for a sequence of promoc_assembly_interfaces__srv__SixDofMotion_Response.
typedef struct promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence
{
  promoc_assembly_interfaces__srv__SixDofMotion_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__STRUCT_H_
