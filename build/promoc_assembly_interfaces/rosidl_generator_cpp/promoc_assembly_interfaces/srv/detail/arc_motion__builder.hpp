// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from promoc_assembly_interfaces:srv/ArcMotion.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__BUILDER_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "promoc_assembly_interfaces/srv/detail/arc_motion__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace promoc_assembly_interfaces
{

namespace srv
{

namespace builder
{

class Init_ArcMotion_Request_angle_radians
{
public:
  explicit Init_ArcMotion_Request_angle_radians(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  ::promoc_assembly_interfaces::srv::ArcMotion_Request angle_radians(::promoc_assembly_interfaces::srv::ArcMotion_Request::_angle_radians_type arg)
  {
    msg_.angle_radians = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_radius_meters
{
public:
  explicit Init_ArcMotion_Request_radius_meters(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_angle_radians radius_meters(::promoc_assembly_interfaces::srv::ArcMotion_Request::_radius_meters_type arg)
  {
    msg_.radius_meters = std::move(arg);
    return Init_ArcMotion_Request_angle_radians(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_xy_max_accl
{
public:
  explicit Init_ArcMotion_Request_xy_max_accl(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_radius_meters xy_max_accl(::promoc_assembly_interfaces::srv::ArcMotion_Request::_xy_max_accl_type arg)
  {
    msg_.xy_max_accl = std::move(arg);
    return Init_ArcMotion_Request_radius_meters(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_xy_max_speed
{
public:
  explicit Init_ArcMotion_Request_xy_max_speed(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_xy_max_accl xy_max_speed(::promoc_assembly_interfaces::srv::ArcMotion_Request::_xy_max_speed_type arg)
  {
    msg_.xy_max_speed = std::move(arg);
    return Init_ArcMotion_Request_xy_max_accl(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_final_speed
{
public:
  explicit Init_ArcMotion_Request_final_speed(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_xy_max_speed final_speed(::promoc_assembly_interfaces::srv::ArcMotion_Request::_final_speed_type arg)
  {
    msg_.final_speed = std::move(arg);
    return Init_ArcMotion_Request_xy_max_speed(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_y_pos
{
public:
  explicit Init_ArcMotion_Request_y_pos(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_final_speed y_pos(::promoc_assembly_interfaces::srv::ArcMotion_Request::_y_pos_type arg)
  {
    msg_.y_pos = std::move(arg);
    return Init_ArcMotion_Request_final_speed(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_x_pos
{
public:
  explicit Init_ArcMotion_Request_x_pos(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_y_pos x_pos(::promoc_assembly_interfaces::srv::ArcMotion_Request::_x_pos_type arg)
  {
    msg_.x_pos = std::move(arg);
    return Init_ArcMotion_Request_y_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_postion_mode
{
public:
  explicit Init_ArcMotion_Request_postion_mode(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_x_pos postion_mode(::promoc_assembly_interfaces::srv::ArcMotion_Request::_postion_mode_type arg)
  {
    msg_.postion_mode = std::move(arg);
    return Init_ArcMotion_Request_x_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_arc_dir
{
public:
  explicit Init_ArcMotion_Request_arc_dir(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_postion_mode arc_dir(::promoc_assembly_interfaces::srv::ArcMotion_Request::_arc_dir_type arg)
  {
    msg_.arc_dir = std::move(arg);
    return Init_ArcMotion_Request_postion_mode(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_arc_type
{
public:
  explicit Init_ArcMotion_Request_arc_type(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_arc_dir arc_type(::promoc_assembly_interfaces::srv::ArcMotion_Request::_arc_type_type arg)
  {
    msg_.arc_type = std::move(arg);
    return Init_ArcMotion_Request_arc_dir(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_arc_mode
{
public:
  explicit Init_ArcMotion_Request_arc_mode(::promoc_assembly_interfaces::srv::ArcMotion_Request & msg)
  : msg_(msg)
  {}
  Init_ArcMotion_Request_arc_type arc_mode(::promoc_assembly_interfaces::srv::ArcMotion_Request::_arc_mode_type arg)
  {
    msg_.arc_mode = std::move(arg);
    return Init_ArcMotion_Request_arc_type(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

class Init_ArcMotion_Request_xbot_id
{
public:
  Init_ArcMotion_Request_xbot_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_ArcMotion_Request_arc_mode xbot_id(::promoc_assembly_interfaces::srv::ArcMotion_Request::_xbot_id_type arg)
  {
    msg_.xbot_id = std::move(arg);
    return Init_ArcMotion_Request_arc_mode(msg_);
  }

private:
  ::promoc_assembly_interfaces::srv::ArcMotion_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::ArcMotion_Request>()
{
  return promoc_assembly_interfaces::srv::builder::Init_ArcMotion_Request_xbot_id();
}

}  // namespace promoc_assembly_interfaces


namespace promoc_assembly_interfaces
{

namespace srv
{


}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::srv::ArcMotion_Response>()
{
  return ::promoc_assembly_interfaces::srv::ArcMotion_Response(rosidl_runtime_cpp::MessageInitialization::ZERO);
}

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__BUILDER_HPP_
