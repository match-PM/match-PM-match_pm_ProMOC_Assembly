// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from promoc_assembly_interfaces:msg/Test.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__BUILDER_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "promoc_assembly_interfaces/msg/detail/test__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace promoc_assembly_interfaces
{

namespace msg
{

namespace builder
{

class Init_Test_message
{
public:
  Init_Test_message()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::promoc_assembly_interfaces::msg::Test message(::promoc_assembly_interfaces::msg::Test::_message_type arg)
  {
    msg_.message = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::msg::Test msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::msg::Test>()
{
  return promoc_assembly_interfaces::msg::builder::Init_Test_message();
}

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__TEST__BUILDER_HPP_
