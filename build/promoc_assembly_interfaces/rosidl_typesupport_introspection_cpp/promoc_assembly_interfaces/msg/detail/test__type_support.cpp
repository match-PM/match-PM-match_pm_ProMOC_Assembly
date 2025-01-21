// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from promoc_assembly_interfaces:msg/Test.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "promoc_assembly_interfaces/msg/detail/test__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace promoc_assembly_interfaces
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void Test_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) promoc_assembly_interfaces::msg::Test(_init);
}

void Test_fini_function(void * message_memory)
{
  auto typed_message = static_cast<promoc_assembly_interfaces::msg::Test *>(message_memory);
  typed_message->~Test();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember Test_message_member_array[1] = {
  {
    "message",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(promoc_assembly_interfaces::msg::Test, message),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers Test_message_members = {
  "promoc_assembly_interfaces::msg",  // message namespace
  "Test",  // message name
  1,  // number of fields
  sizeof(promoc_assembly_interfaces::msg::Test),
  Test_message_member_array,  // message members
  Test_init_function,  // function to initialize message memory (memory has to be allocated)
  Test_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t Test_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &Test_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace promoc_assembly_interfaces


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<promoc_assembly_interfaces::msg::Test>()
{
  return &::promoc_assembly_interfaces::msg::rosidl_typesupport_introspection_cpp::Test_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, promoc_assembly_interfaces, msg, Test)() {
  return &::promoc_assembly_interfaces::msg::rosidl_typesupport_introspection_cpp::Test_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
