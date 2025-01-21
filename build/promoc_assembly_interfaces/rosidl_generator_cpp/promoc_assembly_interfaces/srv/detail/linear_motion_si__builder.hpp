// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from promoc_assembly_interfaces:srv/LinearMotionSi.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LINEAR_MOTION_SI__BUILDER_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LINEAR_MOTION_SI__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "promoc_assembly_interfaces/srv/detail/linear_motion_si__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_LinearMotionSi_Request_xy_max_accl
{
public:
  explicit Init_LinearMotionSi_Request_xy_max_accl(::promoc_assembly_interfaces::srv::LinearMotionSi_Request & msg)
  : msg_(msg)
  {}
  ::promoc_assembly_interfaces::srv::LinearMotionSi_Request xy_max_accl(::promoc_assembly_interfaces::srv::LinearMotionSi_Request::_xy_max_accl_type arg)
  {
    msg_.xy_max_accl = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LinearMotionSi_Request msg_;
};

class Init_LinearMotionSi_Request_xy_max_speed
{
public:
  explicit Init_LinearMotionSi_Request_xy_max_speed(::promoc_assembly_interfaces::srv::LinearMotionSi_Request & msg)
  : msg_(msg)
  {}
  Init_LinearMotionSi_Request_xy_max_accl xy_max_speed(::promoc_assembly_interfaces::srv::LinearMotionSi_Request::_xy_max_speed_type arg)
  {
    msg_.xy_max_speed = std::move(arg);
    return Init_LinearMotionSi_Request_xy_max_accl(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LinearMotionSi_Request msg_;
};

class Init_LinearMotionSi_Request_y_pos
{
public:
  explicit Init_LinearMotionSi_Request_y_pos(::promoc_assembly_interfaces::srv::LinearMotionSi_Request & msg)
  : msg_(msg)
  {}
  Init_LinearMotionSi_Request_xy_max_speed y_pos(::promoc_assembly_interfaces::srv::LinearMotionSi_Request::_y_pos_type arg)
  {
    msg_.y_pos = std::move(arg);
    return Init_LinearMotionSi_Request_xy_max_speed(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LinearMotionSi_Request msg_;
};

class Init_LinearMotionSi_Request_x_pos
{
public:
  explicit Init_LinearMotionSi_Request_x_pos(::promoc_assembly_interfaces::srv::LinearMotionSi_Request & msg)
  : msg_(msg)
  {}
  Init_LinearMotionSi_Request_y_pos x_pos(::promoc_assembly_interfaces::srv::LinearMotionSi_Request::_x_pos_type arg)
  {
    msg_.x_pos = std::move(arg);
    return Init_LinearMotionSi_Request_y_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LinearMotionSi_Request msg_;
};

class Init_LinearMotionSi_Request_xbot_id
{
public:
  Init_LinearMotionSi_Request_xbot_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_LinearMotionSi_Request_x_pos xbot_id(::promoc_assembly_interfaces::srv::LinearMotionSi_Request::_xbot_id_type arg)
  {
    msg_.xbot_id = std::move(arg);
    return Init_LinearMotionSi_Request_x_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LinearMotionSi_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::LinearMotionSi_Request>()
{
  return promoc_assembly_interfaces::srv::builder::Init_LinearMotionSi_Request_xbot_id();
}

}  // namespace promoc_assembly_interfaces


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_LinearMotionSi_Response_finished
{
public:
  Init_LinearMotionSi_Response_finished()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::promoc_assembly_interfaces::srv::LinearMotionSi_Response finished(::promoc_assembly_interfaces::srv::LinearMotionSi_Response::_finished_type arg)
  {
    msg_.finished = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::LinearMotionSi_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::LinearMotionSi_Response>()
{
  return promoc_assembly_interfaces::srv::builder::Init_LinearMotionSi_Response_finished();
}

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__LINEAR_MOTION_SI__BUILDER_HPP_
