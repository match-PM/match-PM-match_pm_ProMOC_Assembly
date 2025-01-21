// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__STRUCT_H_
#define PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/XBotInfo in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__msg__XBotInfo
{
  double x_pos;
  double y_pos;
  double z_pos;
  double rx_pos;
  double ry_pos;
  double rz_pos;
} promoc_assembly_interfaces__msg__XBotInfo;

// Struct for a sequence of promoc_assembly_interfaces__msg__XBotInfo.
typedef struct promoc_assembly_interfaces__msg__XBotInfo__Sequence
{
  promoc_assembly_interfaces__msg__XBotInfo * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__msg__XBotInfo__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__STRUCT_H_
