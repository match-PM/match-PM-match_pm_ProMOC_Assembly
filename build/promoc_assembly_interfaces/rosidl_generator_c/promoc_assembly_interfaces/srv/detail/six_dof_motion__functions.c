// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from promoc_assembly_interfaces:srv/SixDofMotion.idl
// generated code does not contain a copyright notice
#include "promoc_assembly_interfaces/srv/detail/six_dof_motion__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

bool
promoc_assembly_interfaces__srv__SixDofMotion_Request__init(promoc_assembly_interfaces__srv__SixDofMotion_Request * msg)
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
  // xy_max_speed
  // xy_max_accl
  // z_max_speed
  // rx_max_speed
  // ry_max_speed
  // rz_max_speed
  return true;
}

void
promoc_assembly_interfaces__srv__SixDofMotion_Request__fini(promoc_assembly_interfaces__srv__SixDofMotion_Request * msg)
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
  // xy_max_speed
  // xy_max_accl
  // z_max_speed
  // rx_max_speed
  // ry_max_speed
  // rz_max_speed
}

bool
promoc_assembly_interfaces__srv__SixDofMotion_Request__are_equal(const promoc_assembly_interfaces__srv__SixDofMotion_Request * lhs, const promoc_assembly_interfaces__srv__SixDofMotion_Request * rhs)
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
  // xy_max_speed
  if (lhs->xy_max_speed != rhs->xy_max_speed) {
    return false;
  }
  // xy_max_accl
  if (lhs->xy_max_accl != rhs->xy_max_accl) {
    return false;
  }
  // z_max_speed
  if (lhs->z_max_speed != rhs->z_max_speed) {
    return false;
  }
  // rx_max_speed
  if (lhs->rx_max_speed != rhs->rx_max_speed) {
    return false;
  }
  // ry_max_speed
  if (lhs->ry_max_speed != rhs->ry_max_speed) {
    return false;
  }
  // rz_max_speed
  if (lhs->rz_max_speed != rhs->rz_max_speed) {
    return false;
  }
  return true;
}

bool
promoc_assembly_interfaces__srv__SixDofMotion_Request__copy(
  const promoc_assembly_interfaces__srv__SixDofMotion_Request * input,
  promoc_assembly_interfaces__srv__SixDofMotion_Request * output)
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
  // xy_max_speed
  output->xy_max_speed = input->xy_max_speed;
  // xy_max_accl
  output->xy_max_accl = input->xy_max_accl;
  // z_max_speed
  output->z_max_speed = input->z_max_speed;
  // rx_max_speed
  output->rx_max_speed = input->rx_max_speed;
  // ry_max_speed
  output->ry_max_speed = input->ry_max_speed;
  // rz_max_speed
  output->rz_max_speed = input->rz_max_speed;
  return true;
}

promoc_assembly_interfaces__srv__SixDofMotion_Request *
promoc_assembly_interfaces__srv__SixDofMotion_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__SixDofMotion_Request * msg = (promoc_assembly_interfaces__srv__SixDofMotion_Request *)allocator.allocate(sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Request));
  bool success = promoc_assembly_interfaces__srv__SixDofMotion_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
promoc_assembly_interfaces__srv__SixDofMotion_Request__destroy(promoc_assembly_interfaces__srv__SixDofMotion_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    promoc_assembly_interfaces__srv__SixDofMotion_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence__init(promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__SixDofMotion_Request * data = NULL;

  if (size) {
    data = (promoc_assembly_interfaces__srv__SixDofMotion_Request *)allocator.zero_allocate(size, sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = promoc_assembly_interfaces__srv__SixDofMotion_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        promoc_assembly_interfaces__srv__SixDofMotion_Request__fini(&data[i - 1]);
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
promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence__fini(promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence * array)
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
      promoc_assembly_interfaces__srv__SixDofMotion_Request__fini(&array->data[i]);
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

promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence *
promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence * array = (promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence *)allocator.allocate(sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence__destroy(promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence__are_equal(const promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence * lhs, const promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!promoc_assembly_interfaces__srv__SixDofMotion_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence__copy(
  const promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence * input,
  promoc_assembly_interfaces__srv__SixDofMotion_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    promoc_assembly_interfaces__srv__SixDofMotion_Request * data =
      (promoc_assembly_interfaces__srv__SixDofMotion_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!promoc_assembly_interfaces__srv__SixDofMotion_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          promoc_assembly_interfaces__srv__SixDofMotion_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!promoc_assembly_interfaces__srv__SixDofMotion_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


bool
promoc_assembly_interfaces__srv__SixDofMotion_Response__init(promoc_assembly_interfaces__srv__SixDofMotion_Response * msg)
{
  if (!msg) {
    return false;
  }
  // finished
  return true;
}

void
promoc_assembly_interfaces__srv__SixDofMotion_Response__fini(promoc_assembly_interfaces__srv__SixDofMotion_Response * msg)
{
  if (!msg) {
    return;
  }
  // finished
}

bool
promoc_assembly_interfaces__srv__SixDofMotion_Response__are_equal(const promoc_assembly_interfaces__srv__SixDofMotion_Response * lhs, const promoc_assembly_interfaces__srv__SixDofMotion_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // finished
  if (lhs->finished != rhs->finished) {
    return false;
  }
  return true;
}

bool
promoc_assembly_interfaces__srv__SixDofMotion_Response__copy(
  const promoc_assembly_interfaces__srv__SixDofMotion_Response * input,
  promoc_assembly_interfaces__srv__SixDofMotion_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // finished
  output->finished = input->finished;
  return true;
}

promoc_assembly_interfaces__srv__SixDofMotion_Response *
promoc_assembly_interfaces__srv__SixDofMotion_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__SixDofMotion_Response * msg = (promoc_assembly_interfaces__srv__SixDofMotion_Response *)allocator.allocate(sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Response));
  bool success = promoc_assembly_interfaces__srv__SixDofMotion_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
promoc_assembly_interfaces__srv__SixDofMotion_Response__destroy(promoc_assembly_interfaces__srv__SixDofMotion_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    promoc_assembly_interfaces__srv__SixDofMotion_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence__init(promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__SixDofMotion_Response * data = NULL;

  if (size) {
    data = (promoc_assembly_interfaces__srv__SixDofMotion_Response *)allocator.zero_allocate(size, sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = promoc_assembly_interfaces__srv__SixDofMotion_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        promoc_assembly_interfaces__srv__SixDofMotion_Response__fini(&data[i - 1]);
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
promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence__fini(promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence * array)
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
      promoc_assembly_interfaces__srv__SixDofMotion_Response__fini(&array->data[i]);
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

promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence *
promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence * array = (promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence *)allocator.allocate(sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence__destroy(promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence__are_equal(const promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence * lhs, const promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!promoc_assembly_interfaces__srv__SixDofMotion_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence__copy(
  const promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence * input,
  promoc_assembly_interfaces__srv__SixDofMotion_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(promoc_assembly_interfaces__srv__SixDofMotion_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    promoc_assembly_interfaces__srv__SixDofMotion_Response * data =
      (promoc_assembly_interfaces__srv__SixDofMotion_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!promoc_assembly_interfaces__srv__SixDofMotion_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          promoc_assembly_interfaces__srv__SixDofMotion_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!promoc_assembly_interfaces__srv__SixDofMotion_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
