// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from promoc_assembly_interfaces:srv/SixDofMotion.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__BUILDER_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "promoc_assembly_interfaces/srv/detail/six_dof_motion__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_SixDofMotion_Request_rz_max_speed
{
public:
  explicit Init_SixDofMotion_Request_rz_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request rz_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_rz_max_speed_type arg)
  {
    msg_.rz_max_speed = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_ry_max_speed
{
public:
  explicit Init_SixDofMotion_Request_ry_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_rz_max_speed ry_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_ry_max_speed_type arg)
  {
    msg_.ry_max_speed = std::move(arg);
    return Init_SixDofMotion_Request_rz_max_speed(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_rx_max_speed
{
public:
  explicit Init_SixDofMotion_Request_rx_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_ry_max_speed rx_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_rx_max_speed_type arg)
  {
    msg_.rx_max_speed = std::move(arg);
    return Init_SixDofMotion_Request_ry_max_speed(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_z_max_speed
{
public:
  explicit Init_SixDofMotion_Request_z_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_rx_max_speed z_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_z_max_speed_type arg)
  {
    msg_.z_max_speed = std::move(arg);
    return Init_SixDofMotion_Request_rx_max_speed(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_xy_max_accl
{
public:
  explicit Init_SixDofMotion_Request_xy_max_accl(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_z_max_speed xy_max_accl(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_xy_max_accl_type arg)
  {
    msg_.xy_max_accl = std::move(arg);
    return Init_SixDofMotion_Request_z_max_speed(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_xy_max_speed
{
public:
  explicit Init_SixDofMotion_Request_xy_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_xy_max_accl xy_max_speed(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_xy_max_speed_type arg)
  {
    msg_.xy_max_speed = std::move(arg);
    return Init_SixDofMotion_Request_xy_max_accl(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_rz_pos
{
public:
  explicit Init_SixDofMotion_Request_rz_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_xy_max_speed rz_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_rz_pos_type arg)
  {
    msg_.rz_pos = std::move(arg);
    return Init_SixDofMotion_Request_xy_max_speed(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_ry_pos
{
public:
  explicit Init_SixDofMotion_Request_ry_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_rz_pos ry_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_ry_pos_type arg)
  {
    msg_.ry_pos = std::move(arg);
    return Init_SixDofMotion_Request_rz_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_rx_pos
{
public:
  explicit Init_SixDofMotion_Request_rx_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_ry_pos rx_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_rx_pos_type arg)
  {
    msg_.rx_pos = std::move(arg);
    return Init_SixDofMotion_Request_ry_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_z_pos
{
public:
  explicit Init_SixDofMotion_Request_z_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_rx_pos z_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_z_pos_type arg)
  {
    msg_.z_pos = std::move(arg);
    return Init_SixDofMotion_Request_rx_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_y_pos
{
public:
  explicit Init_SixDofMotion_Request_y_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request & msg)
  : msg_(msg)
  {}
  Init_SixDofMotion_Request_z_pos y_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_y_pos_type arg)
  {
    msg_.y_pos = std::move(arg);
    return Init_SixDofMotion_Request_z_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

class Init_SixDofMotion_Request_x_pos
{
public:
  Init_SixDofMotion_Request_x_pos()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_SixDofMotion_Request_y_pos x_pos(::promoc_assembly_interfaces::srv::SixDofMotion_Request::_x_pos_type arg)
  {
    msg_.x_pos = std::move(arg);
    return Init_SixDofMotion_Request_y_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::SixDofMotion_Request>()
{
  return promoc_assembly_interfaces::srv::builder::Init_SixDofMotion_Request_x_pos();
}

}  // namespace promoc_assembly_interfaces


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_SixDofMotion_Response_finished
{
public:
  Init_SixDofMotion_Response_finished()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::promoc_assembly_interfaces::srv::SixDofMotion_Response finished(::promoc_assembly_interfaces::srv::SixDofMotion_Response::_finished_type arg)
  {
    msg_.finished = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::SixDofMotion_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::SixDofMotion_Response>()
{
  return promoc_assembly_interfaces::srv::builder::Init_SixDofMotion_Response_finished();
}

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__BUILDER_HPP_
