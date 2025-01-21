// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice
#include "promoc_assembly_interfaces/msg/detail/x_bot_info__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


bool
promoc_assembly_interfaces__msg__XBotInfo__init(promoc_assembly_interfaces__msg__XBotInfo * msg)
{
  if (!msg) {
    return false;
  }
  // x_pos
  // y_pos
  // z_pos
  // rx_pos
  // ry_pos
  // rz_pos
  return true;
}

void
promoc_assembly_interfaces__msg__XBotInfo__fini(promoc_assembly_interfaces__msg__XBotInfo * msg)
{
  if (!msg) {
    return;
  }
  // x_pos
  // y_pos
  // z_pos
  // rx_pos
  // ry_pos
  // rz_pos
}

bool
promoc_assembly_interfaces__msg__XBotInfo__are_equal(const promoc_assembly_interfaces__msg__XBotInfo * lhs, const promoc_assembly_interfaces__msg__XBotInfo * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // x_pos
  if (lhs->x_pos != rhs->x_pos) {
    return false;
  }
  // y_pos
  if (lhs->y_pos != rhs->y_pos) {
    return false;
  }
  // z_pos
  if (lhs->z_pos != rhs->z_pos) {
    return false;
  }
  // rx_pos
  if (lhs->rx_pos != rhs->rx_pos) {
    return false;
  }
  // ry_pos
  if (lhs->ry_pos != rhs->ry_pos) {
    return false;
  }
  // rz_pos
  if (lhs->rz_pos != rhs->rz_pos) {
    return false;
  }
  return true;
}

bool
promoc_assembly_interfaces__msg__XBotInfo__copy(
  const promoc_assembly_interfaces__msg__XBotInfo * input,
  promoc_assembly_interfaces__msg__XBotInfo * output)
{
  if (!input || !output) {
    return false;
  }
  // x_pos
  output->x_pos = input->x_pos;
  // y_pos
  output->y_pos = input->y_pos;
  // z_pos
  output->z_pos = input->z_pos;
  // rx_pos
  output->rx_pos = input->rx_pos;
  // ry_pos
  output->ry_pos = input->ry_pos;
  // rz_pos
  output->rz_pos = input->rz_pos;
  return true;
}

promoc_assembly_interfaces__msg__XBotInfo *
promoc_assembly_interfaces__msg__XBotInfo__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__msg__XBotInfo * msg = (promoc_assembly_interfaces__msg__XBotInfo *)allocator.allocate(sizeof(promoc_assembly_interfaces__msg__XBotInfo), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(promoc_assembly_interfaces__msg__XBotInfo));
  bool success = promoc_assembly_interfaces__msg__XBotInfo__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
promoc_assembly_interfaces__msg__XBotInfo__destroy(promoc_assembly_interfaces__msg__XBotInfo * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    promoc_assembly_interfaces__msg__XBotInfo__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
promoc_assembly_interfaces__msg__XBotInfo__Sequence__init(promoc_assembly_interfaces__msg__XBotInfo__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__msg__XBotInfo * data = NULL;

  if (size) {
    data = (promoc_assembly_interfaces__msg__XBotInfo *)allocator.zero_allocate(size, sizeof(promoc_assembly_interfaces__msg__XBotInfo), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = promoc_assembly_interfaces__msg__XBotInfo__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        promoc_assembly_interfaces__msg__XBotInfo__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
promoc_assembly_interfaces__msg__XBotInfo__Sequence__fini(promoc_assembly_interfaces__msg__XBotInfo__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      promoc_assembly_interfaces__msg__XBotInfo__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

promoc_assembly_interfaces__msg__XBotInfo__Sequence *
promoc_assembly_interfaces__msg__XBotInfo__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__msg__XBotInfo__Sequence * array = (promoc_assembly_interfaces__msg__XBotInfo__Sequence *)allocator.allocate(sizeof(promoc_assembly_interfaces__msg__XBotInfo__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = promoc_assembly_interfaces__msg__XBotInfo__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
promoc_assembly_interfaces__msg__XBotInfo__Sequence__destroy(promoc_assembly_interfaces__msg__XBotInfo__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    promoc_assembly_interfaces__msg__XBotInfo__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
promoc_assembly_interfaces__msg__XBotInfo__Sequence__are_equal(const promoc_assembly_interfaces__msg__XBotInfo__Sequence * lhs, const promoc_assembly_interfaces__msg__XBotInfo__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!promoc_assembly_interfaces__msg__XBotInfo__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
promoc_assembly_interfaces__msg__XBotInfo__Sequence__copy(
  const promoc_assembly_interfaces__msg__XBotInfo__Sequence * input,
  promoc_assembly_interfaces__msg__XBotInfo__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(promoc_assembly_interfaces__msg__XBotInfo);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    promoc_assembly_interfaces__msg__XBotInfo * data =
      (promoc_assembly_interfaces__msg__XBotInfo *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!promoc_assembly_interfaces__msg__XBotInfo__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          promoc_assembly_interfaces__msg__XBotInfo__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!promoc_assembly_interfaces__msg__XBotInfo__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
