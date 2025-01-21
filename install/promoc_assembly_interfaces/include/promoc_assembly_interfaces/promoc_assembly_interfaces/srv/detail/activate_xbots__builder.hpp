// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from promoc_assembly_interfaces:srv/ActivateXbots.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__BUILDER_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "promoc_assembly_interfaces/srv/detail/activate_xbots__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_ActivateXbots_Request_activation_status
{
public:
  explicit Init_ActivateXbots_Request_activation_status(::promoc_assembly_interfaces::srv::ActivateXbots_Request & msg)
  : msg_(msg)
  {}
  ::promoc_assembly_interfaces::srv::ActivateXbots_Request activation_status(::promoc_assembly_interfaces::srv::ActivateXbots_Request::_activation_status_type arg)
  {
    msg_.activation_status = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ActivateXbots_Request msg_;
};

class Init_ActivateXbots_Request_xbot_id
{
public:
  Init_ActivateXbots_Request_xbot_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_ActivateXbots_Request_activation_status xbot_id(::promoc_assembly_interfaces::srv::ActivateXbots_Request::_xbot_id_type arg)
  {
    msg_.xbot_id = std::move(arg);
    return Init_ActivateXbots_Request_activation_status(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ActivateXbots_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::ActivateXbots_Request>()
{
  return promoc_assembly_interfaces::srv::builder::Init_ActivateXbots_Request_xbot_id();
}

}  // namespace promoc_assembly_interfaces


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_ActivateXbots_Response_activation_status
{
public:
  Init_ActivateXbots_Response_activation_status()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::promoc_assembly_interfaces::srv::ActivateXbots_Response activation_status(::promoc_assembly_interfaces::srv::ActivateXbots_Response::_activation_status_type arg)
  {
    msg_.activation_status = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ActivateXbots_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::ActivateXbots_Response>()
{
  return promoc_assembly_interfaces::srv::builder::Init_ActivateXbots_Response_activation_status();
}

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__BUILDER_HPP_
