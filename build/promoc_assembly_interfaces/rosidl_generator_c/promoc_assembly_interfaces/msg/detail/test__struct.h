// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from promoc_assembly_interfaces:msg/Test.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__STRUCT_H_
#define PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'message'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/Test in the package promoc_assembly_interfaces.
typedef struct promoc_assembly_interfaces__msg__Test
{
  rosidl_runtime_c__String message;
} promoc_assembly_interfaces__msg__Test;

// Struct for a sequence of promoc_assembly_interfaces__msg__Test.
typedef struct promoc_assembly_interfaces__msg__Test__Sequence
{
  promoc_assembly_interfaces__msg__Test * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} promoc_assembly_interfaces__msg__Test__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__STRUCT_H_
