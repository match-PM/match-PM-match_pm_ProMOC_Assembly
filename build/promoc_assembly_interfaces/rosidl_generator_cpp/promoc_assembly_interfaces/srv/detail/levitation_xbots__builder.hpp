// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from promoc_assembly_interfaces:srv/LevitationXbots.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LEVITATION_XBOTS__BUILDER_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LEVITATION_XBOTS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "promoc_assembly_interfaces/srv/detail/levitation_xbots__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_LevitationXbots_Request_levitation
{
public:
  explicit Init_LevitationXbots_Request_levitation(::promoc_assembly_interfaces::srv::LevitationXbots_Request & msg)
  : msg_(msg)
  {}
  ::promoc_assembly_interfaces::srv::LevitationXbots_Request levitation(::promoc_assembly_interfaces::srv::LevitationXbots_Request::_levitation_type arg)
  {
    msg_.levitation = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LevitationXbots_Request msg_;
};

class Init_LevitationXbots_Request_xbot_id
{
public:
  Init_LevitationXbots_Request_xbot_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_LevitationXbots_Request_levitation xbot_id(::promoc_assembly_interfaces::srv::LevitationXbots_Request::_xbot_id_type arg)
  {
    msg_.xbot_id = std::move(arg);
    return Init_LevitationXbots_Request_levitation(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LevitationXbots_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::LevitationXbots_Request>()
{
  return promoc_assembly_interfaces::srv::builder::Init_LevitationXbots_Request_xbot_id();
}

}  // namespace promoc_assembly_interfaces


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_LevitationXbots_Response_levitation
{
public:
  Init_LevitationXbots_Response_levitation()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::promoc_assembly_interfaces::srv::LevitationXbots_Response levitation(::promoc_assembly_interfaces::srv::LevitationXbots_Response::_levitation_type arg)
  {
    msg_.levitation = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LevitationXbots_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::LevitationXbots_Response>()
{
  return promoc_assembly_interfaces::srv::builder::Init_LevitationXbots_Response_levitation();
}

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LEVITATION_XBOTS__BUILDER_HPP_
