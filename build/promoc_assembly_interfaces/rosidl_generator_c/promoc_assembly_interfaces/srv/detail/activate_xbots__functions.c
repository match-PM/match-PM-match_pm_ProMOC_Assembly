// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from promoc_assembly_interfaces:srv/ActivateXbots.idl
// generated code does not contain a copyright notice
#include "promoc_assembly_interfaces/srv/detail/activate_xbots__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

bool
promoc_assembly_interfaces__srv__ActivateXbots_Request__init(promoc_assembly_interfaces__srv__ActivateXbots_Request * msg)
{
  if (!msg) {
    return false;
  }
  // xbot_id
  // activation_status
  return true;
}

void
promoc_assembly_interfaces__srv__ActivateXbots_Request__fini(promoc_assembly_interfaces__srv__ActivateXbots_Request * msg)
{
  if (!msg) {
    return;
  }
  // xbot_id
  // activation_status
}

bool
promoc_assembly_interfaces__srv__ActivateXbots_Request__are_equal(const promoc_assembly_interfaces__srv__ActivateXbots_Request * lhs, const promoc_assembly_interfaces__srv__ActivateXbots_Request * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // xbot_id
  if (lhs->xbot_id != rhs->xbot_id) {
    return false;
  }
  // activation_status
  if (lhs->activation_status != rhs->activation_status) {
    return false;
  }
  return true;
}

bool
promoc_assembly_interfaces__srv__ActivateXbots_Request__copy(
  const promoc_assembly_interfaces__srv__ActivateXbots_Request * input,
  promoc_assembly_interfaces__srv__ActivateXbots_Request * output)
{
  if (!input || !output) {
    return false;
  }
  // xbot_id
  output->xbot_id = input->xbot_id;
  // activation_status
  output->activation_status = input->activation_status;
  return true;
}

promoc_assembly_interfaces__srv__ActivateXbots_Request *
promoc_assembly_interfaces__srv__ActivateXbots_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__ActivateXbots_Request * msg = (promoc_assembly_interfaces__srv__ActivateXbots_Request *)allocator.allocate(sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Request));
  bool success = promoc_assembly_interfaces__srv__ActivateXbots_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
promoc_assembly_interfaces__srv__ActivateXbots_Request__destroy(promoc_assembly_interfaces__srv__ActivateXbots_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    promoc_assembly_interfaces__srv__ActivateXbots_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence__init(promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__ActivateXbots_Request * data = NULL;

  if (size) {
    data = (promoc_assembly_interfaces__srv__ActivateXbots_Request *)allocator.zero_allocate(size, sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = promoc_assembly_interfaces__srv__ActivateXbots_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        promoc_assembly_interfaces__srv__ActivateXbots_Request__fini(&data[i - 1]);
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
promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence__fini(promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence * array)
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
      promoc_assembly_interfaces__srv__ActivateXbots_Request__fini(&array->data[i]);
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

promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence *
promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence * array = (promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence *)allocator.allocate(sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence__destroy(promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence__are_equal(const promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence * lhs, const promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!promoc_assembly_interfaces__srv__ActivateXbots_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence__copy(
  const promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence * input,
  promoc_assembly_interfaces__srv__ActivateXbots_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    promoc_assembly_interfaces__srv__ActivateXbots_Request * data =
      (promoc_assembly_interfaces__srv__ActivateXbots_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!promoc_assembly_interfaces__srv__ActivateXbots_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          promoc_assembly_interfaces__srv__ActivateXbots_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!promoc_assembly_interfaces__srv__ActivateXbots_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


bool
promoc_assembly_interfaces__srv__ActivateXbots_Response__init(promoc_assembly_interfaces__srv__ActivateXbots_Response * msg)
{
  if (!msg) {
    return false;
  }
  // activation_status
  return true;
}

void
promoc_assembly_interfaces__srv__ActivateXbots_Response__fini(promoc_assembly_interfaces__srv__ActivateXbots_Response * msg)
{
  if (!msg) {
    return;
  }
  // activation_status
}

bool
promoc_assembly_interfaces__srv__ActivateXbots_Response__are_equal(const promoc_assembly_interfaces__srv__ActivateXbots_Response * lhs, const promoc_assembly_interfaces__srv__ActivateXbots_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // activation_status
  if (lhs->activation_status != rhs->activation_status) {
    return false;
  }
  return true;
}

bool
promoc_assembly_interfaces__srv__ActivateXbots_Response__copy(
  const promoc_assembly_interfaces__srv__ActivateXbots_Response * input,
  promoc_assembly_interfaces__srv__ActivateXbots_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // activation_status
  output->activation_status = input->activation_status;
  return true;
}

promoc_assembly_interfaces__srv__ActivateXbots_Response *
promoc_assembly_interfaces__srv__ActivateXbots_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__ActivateXbots_Response * msg = (promoc_assembly_interfaces__srv__ActivateXbots_Response *)allocator.allocate(sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Response));
  bool success = promoc_assembly_interfaces__srv__ActivateXbots_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
promoc_assembly_interfaces__srv__ActivateXbots_Response__destroy(promoc_assembly_interfaces__srv__ActivateXbots_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    promoc_assembly_interfaces__srv__ActivateXbots_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence__init(promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__ActivateXbots_Response * data = NULL;

  if (size) {
    data = (promoc_assembly_interfaces__srv__ActivateXbots_Response *)allocator.zero_allocate(size, sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = promoc_assembly_interfaces__srv__ActivateXbots_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        promoc_assembly_interfaces__srv__ActivateXbots_Response__fini(&data[i - 1]);
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
promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence__fini(promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence * array)
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
      promoc_assembly_interfaces__srv__ActivateXbots_Response__fini(&array->data[i]);
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

promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence *
promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence * array = (promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence *)allocator.allocate(sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence__destroy(promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence__are_equal(const promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence * lhs, const promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!promoc_assembly_interfaces__srv__ActivateXbots_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence__copy(
  const promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence * input,
  promoc_assembly_interfaces__srv__ActivateXbots_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(promoc_assembly_interfaces__srv__ActivateXbots_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    promoc_assembly_interfaces__srv__ActivateXbots_Response * data =
      (promoc_assembly_interfaces__srv__ActivateXbots_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!promoc_assembly_interfaces__srv__ActivateXbots_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          promoc_assembly_interfaces__srv__ActivateXbots_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!promoc_assembly_interfaces__srv__ActivateXbots_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
