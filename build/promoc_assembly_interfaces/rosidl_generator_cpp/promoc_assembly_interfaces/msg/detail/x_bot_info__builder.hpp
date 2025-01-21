// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__BUILDER_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "promoc_assembly_interfaces/msg/detail/x_bot_info__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace promoc_assembly_interfaces
{

namespace msg
{

namespace builder
{

class Init_XBotInfo_rz_pos
{
public:
  explicit Init_XBotInfo_rz_pos(::promoc_assembly_interfaces::msg::XBotInfo & msg)
  : msg_(msg)
  {}
  ::promoc_assembly_interfaces::msg::XBotInfo rz_pos(::promoc_assembly_interfaces::msg::XBotInfo::_rz_pos_type arg)
  {
    msg_.rz_pos = std::move(arg);
    return std::move(msg_);
  }

private:
  ::promoc_assembly_interfaces::msg::XBotInfo msg_;
};

class Init_XBotInfo_ry_pos
{
public:
  explicit Init_XBotInfo_ry_pos(::promoc_assembly_interfaces::msg::XBotInfo & msg)
  : msg_(msg)
  {}
  Init_XBotInfo_rz_pos ry_pos(::promoc_assembly_interfaces::msg::XBotInfo::_ry_pos_type arg)
  {
    msg_.ry_pos = std::move(arg);
    return Init_XBotInfo_rz_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::msg::XBotInfo msg_;
};

class Init_XBotInfo_rx_pos
{
public:
  explicit Init_XBotInfo_rx_pos(::promoc_assembly_interfaces::msg::XBotInfo & msg)
  : msg_(msg)
  {}
  Init_XBotInfo_ry_pos rx_pos(::promoc_assembly_interfaces::msg::XBotInfo::_rx_pos_type arg)
  {
    msg_.rx_pos = std::move(arg);
    return Init_XBotInfo_ry_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::msg::XBotInfo msg_;
};

class Init_XBotInfo_z_pos
{
public:
  explicit Init_XBotInfo_z_pos(::promoc_assembly_interfaces::msg::XBotInfo & msg)
  : msg_(msg)
  {}
  Init_XBotInfo_rx_pos z_pos(::promoc_assembly_interfaces::msg::XBotInfo::_z_pos_type arg)
  {
    msg_.z_pos = std::move(arg);
    return Init_XBotInfo_rx_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::msg::XBotInfo msg_;
};

class Init_XBotInfo_y_pos
{
public:
  explicit Init_XBotInfo_y_pos(::promoc_assembly_interfaces::msg::XBotInfo & msg)
  : msg_(msg)
  {}
  Init_XBotInfo_z_pos y_pos(::promoc_assembly_interfaces::msg::XBotInfo::_y_pos_type arg)
  {
    msg_.y_pos = std::move(arg);
    return Init_XBotInfo_z_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::msg::XBotInfo msg_;
};

class Init_XBotInfo_x_pos
{
public:
  Init_XBotInfo_x_pos()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_XBotInfo_y_pos x_pos(::promoc_assembly_interfaces::msg::XBotInfo::_x_pos_type arg)
  {
    msg_.x_pos = std::move(arg);
    return Init_XBotInfo_y_pos(msg_);
  }

private:
  ::promoc_assembly_interfaces::msg::XBotInfo msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::promoc_assembly_interfaces::msg::XBotInfo>()
{
  return promoc_assembly_interfaces::msg::builder::Init_XBotInfo_x_pos();
}

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__BUILDER_HPP_
