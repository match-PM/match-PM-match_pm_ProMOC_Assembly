// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from promoc_assembly_interfaces:msg/Test.idl
// generated code does not contain a copyright notice
#include "promoc_assembly_interfaces/msg/detail/test__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `message`
#include "rosidl_runtime_c/string_functions.h"

bool
promoc_assembly_interfaces__msg__Test__init(promoc_assembly_interfaces__msg__Test * msg)
{
  if (!msg) {
    return false;
  }
  // message
  if (!rosidl_runtime_c__String__init(&msg->message)) {
    promoc_assembly_interfaces__msg__Test__fini(msg);
    return false;
  }
  return true;
}

void
promoc_assembly_interfaces__msg__Test__fini(promoc_assembly_interfaces__msg__Test * msg)
{
  if (!msg) {
    return;
  }
  // message
  rosidl_runtime_c__String__fini(&msg->message);
}

bool
promoc_assembly_interfaces__msg__Test__are_equal(const promoc_assembly_interfaces__msg__Test * lhs, const promoc_assembly_interfaces__msg__Test * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // message
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->message), &(rhs->message)))
  {
    return false;
  }
  return true;
}

bool
promoc_assembly_interfaces__msg__Test__copy(
  const promoc_assembly_interfaces__msg__Test * input,
  promoc_assembly_interfaces__msg__Test * output)
{
  if (!input || !output) {
    return false;
  }
  // message
  if (!rosidl_runtime_c__String__copy(
      &(input->message), &(output->message)))
  {
    return false;
  }
  return true;
}

promoc_assembly_interfaces__msg__Test *
promoc_assembly_interfaces__msg__Test__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__msg__Test * msg = (promoc_assembly_interfaces__msg__Test *)allocator.allocate(sizeof(promoc_assembly_interfaces__msg__Test), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(promoc_assembly_interfaces__msg__Test));
  bool success = promoc_assembly_interfaces__msg__Test__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
promoc_assembly_interfaces__msg__Test__destroy(promoc_assembly_interfaces__msg__Test * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    promoc_assembly_interfaces__msg__Test__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
promoc_assembly_interfaces__msg__Test__Sequence__init(promoc_assembly_interfaces__msg__Test__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__msg__Test * data = NULL;

  if (size) {
    data = (promoc_assembly_interfaces__msg__Test *)allocator.zero_allocate(size, sizeof(promoc_assembly_interfaces__msg__Test), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = promoc_assembly_interfaces__msg__Test__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        promoc_assembly_interfaces__msg__Test__fini(&data[i - 1]);
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
promoc_assembly_interfaces__msg__Test__Sequence__fini(promoc_assembly_interfaces__msg__Test__Sequence * array)
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
      promoc_assembly_interfaces__msg__Test__fini(&array->data[i]);
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

promoc_assembly_interfaces__msg__Test__Sequence *
promoc_assembly_interfaces__msg__Test__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  promoc_assembly_interfaces__msg__Test__Sequence * array = (promoc_assembly_interfaces__msg__Test__Sequence *)allocator.allocate(sizeof(promoc_assembly_interfaces__msg__Test__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = promoc_assembly_interfaces__msg__Test__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
promoc_assembly_interfaces__msg__Test__Sequence__destroy(promoc_assembly_interfaces__msg__Test__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    promoc_assembly_interfaces__msg__Test__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
promoc_assembly_interfaces__msg__Test__Sequence__are_equal(const promoc_assembly_interfaces__msg__Test__Sequence * lhs, const promoc_assembly_interfaces__msg__Test__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!promoc_assembly_interfaces__msg__Test__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
promoc_assembly_interfaces__msg__Test__Sequence__copy(
  const promoc_assembly_interfaces__msg__Test__Sequence * input,
  promoc_assembly_interfaces__msg__Test__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(promoc_assembly_interfaces__msg__Test);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    promoc_assembly_interfaces__msg__Test * data =
      (promoc_assembly_interfaces__msg__Test *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!promoc_assembly_interfaces__msg__Test__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          promoc_assembly_interfaces__msg__Test__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!promoc_assembly_interfaces__msg__Test__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
