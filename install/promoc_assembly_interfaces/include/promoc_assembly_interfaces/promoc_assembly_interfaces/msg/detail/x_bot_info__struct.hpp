// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from promoc_assembly_interfaces:msg/XBotInfo.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__STRUCT_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__promoc_assembly_interfaces__msg__XBotInfo __attribute__((deprecated))
#else
# define DEPRECATED__promoc_assembly_interfaces__msg__XBotInfo __declspec(deprecated)
#endif

namespace promoc_assembly_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct XBotInfo_
{
  using Type = XBotInfo_<ContainerAllocator>;

  explicit XBotInfo_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->x_pos = 0.0;
      this->y_pos = 0.0;
      this->z_pos = 0.0;
      this->rx_pos = 0.0;
      this->ry_pos = 0.0;
      this->rz_pos = 0.0;
    }
  }

  explicit XBotInfo_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->x_pos = 0.0;
      this->y_pos = 0.0;
      this->z_pos = 0.0;
      this->rx_pos = 0.0;
      this->ry_pos = 0.0;
      this->rz_pos = 0.0;
    }
  }

  // field types and members
  using _x_pos_type =
    double;
  _x_pos_type x_pos;
  using _y_pos_type =
    double;
  _y_pos_type y_pos;
  using _z_pos_type =
    double;
  _z_pos_type z_pos;
  using _rx_pos_type =
    double;
  _rx_pos_type rx_pos;
  using _ry_pos_type =
    double;
  _ry_pos_type ry_pos;
  using _rz_pos_type =
    double;
  _rz_pos_type rz_pos;

  // setters for named parameter idiom
  Type & set__x_pos(
    const double & _arg)
  {
    this->x_pos = _arg;
    return *this;
  }
  Type & set__y_pos(
    const double & _arg)
  {
    this->y_pos = _arg;
    return *this;
  }
  Type & set__z_pos(
    const double & _arg)
  {
    this->z_pos = _arg;
    return *this;
  }
  Type & set__rx_pos(
    const double & _arg)
  {
    this->rx_pos = _arg;
    return *this;
  }
  Type & set__ry_pos(
    const double & _arg)
  {
    this->ry_pos = _arg;
    return *this;
  }
  Type & set__rz_pos(
    const double & _arg)
  {
    this->rz_pos = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator> *;
  using ConstRawPtr =
    const promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__promoc_assembly_interfaces__msg__XBotInfo
    std::shared_ptr<promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__promoc_assembly_interfaces__msg__XBotInfo
    std::shared_ptr<promoc_assembly_interfaces::msg::XBotInfo_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const XBotInfo_ & other) const
  {
    if (this->x_pos != other.x_pos) {
      return false;
    }
    if (this->y_pos != other.y_pos) {
      return false;
    }
    if (this->z_pos != other.z_pos) {
      return false;
    }
    if (this->rx_pos != other.rx_pos) {
      return false;
    }
    if (this->ry_pos != other.ry_pos) {
      return false;
    }
    if (this->rz_pos != other.rz_pos) {
      return false;
    }
    return true;
  }
  bool operator!=(const XBotInfo_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct XBotInfo_

// alias to use template instance with default allocator
using XBotInfo =
  promoc_assembly_interfaces::msg::XBotInfo_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__MSG__DETAIL__X_BOT_INFO__STRUCT_HPP_
