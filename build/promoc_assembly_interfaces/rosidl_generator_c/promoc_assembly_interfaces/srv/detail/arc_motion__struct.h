// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from promoc_assembly_interfaces:srv/ArcMotion.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__STRUCT_H_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in srv/ArcMotion in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__srv__ArcMotion_Request
{
  int32_t xbot_id;
  int32_t arc_mode;
  int32_t arc_type;
  int32_t arc_dir;
  int32_t postion_mode;
  double x_pos;
  double y_pos;
  double final_speed;
  double xy_max_speed;
  double xy_max_accl;
  double radius_meters;
  double angle_radians;
} promoc_assembly_interfaces__srv__ArcMotion_Request;

// Struct for a sequence of promoc_assembly_interfaces__srv__ArcMotion_Request.
typedef struct promoc_assembly_interfaces__srv__ArcMotion_Request__Sequence
{
  promoc_assembly_interfaces__srv__ArcMotion_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__srv__ArcMotion_Request__Sequence;


// Constants defined in the message

/// Struct defined in srv/ArcMotion in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__srv__ArcMotion_Response
{
  uint8_t structure_needs_at_least_one_member;
} promoc_assembly_interfaces__srv__ArcMotion_Response;

// Struct for a sequence of promoc_assembly_interfaces__srv__ArcMotion_Response.
typedef struct promoc_assembly_interfaces__srv__ArcMotion_Response__Sequence
{
  promoc_assembly_interfaces__srv__ArcMotion_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__srv__ArcMotion_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__STRUCT_H_
