// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from promoc_assembly_interfaces:srv/SixDofMotion.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__STRUCT_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__promoc_assembly_interfaces__srv__SixDofMotion_Request __attribute__((deprecated))
#else
# define DEPRECATED__promoc_assembly_interfaces__srv__SixDofMotion_Request __declspec(deprecated)
#endif

namespace promoc_assembly_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct SixDofMotion_Request_
{
  using Type = SixDofMotion_Request_<ContainerAllocator>;

  explicit SixDofMotion_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
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
      this->xy_max_speed = 0.0;
      this->xy_max_accl = 0.0;
      this->z_max_speed = 0.0;
      this->rx_max_speed = 0.0;
      this->ry_max_speed = 0.0;
      this->rz_max_speed = 0.0;
    }
  }

  explicit SixDofMotion_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
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
      this->xy_max_speed = 0.0;
      this->xy_max_accl = 0.0;
      this->z_max_speed = 0.0;
      this->rx_max_speed = 0.0;
      this->ry_max_speed = 0.0;
      this->rz_max_speed = 0.0;
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
  using _xy_max_speed_type =
    double;
  _xy_max_speed_type xy_max_speed;
  using _xy_max_accl_type =
    double;
  _xy_max_accl_type xy_max_accl;
  using _z_max_speed_type =
    double;
  _z_max_speed_type z_max_speed;
  using _rx_max_speed_type =
    double;
  _rx_max_speed_type rx_max_speed;
  using _ry_max_speed_type =
    double;
  _ry_max_speed_type ry_max_speed;
  using _rz_max_speed_type =
    double;
  _rz_max_speed_type rz_max_speed;

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
  Type & set__xy_max_speed(
    const double & _arg)
  {
    this->xy_max_speed = _arg;
    return *this;
  }
  Type & set__xy_max_accl(
    const double & _arg)
  {
    this->xy_max_accl = _arg;
    return *this;
  }
  Type & set__z_max_speed(
    const double & _arg)
  {
    this->z_max_speed = _arg;
    return *this;
  }
  Type & set__rx_max_speed(
    const double & _arg)
  {
    this->rx_max_speed = _arg;
    return *this;
  }
  Type & set__ry_max_speed(
    const double & _arg)
  {
    this->ry_max_speed = _arg;
    return *this;
  }
  Type & set__rz_max_speed(
    const double & _arg)
  {
    this->rz_max_speed = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__promoc_assembly_interfaces__srv__SixDofMotion_Request
    std::shared_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__promoc_assembly_interfaces__srv__SixDofMotion_Request
    std::shared_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SixDofMotion_Request_ & other) const
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
    if (this->xy_max_speed != other.xy_max_speed) {
      return false;
    }
    if (this->xy_max_accl != other.xy_max_accl) {
      return false;
    }
    if (this->z_max_speed != other.z_max_speed) {
      return false;
    }
    if (this->rx_max_speed != other.rx_max_speed) {
      return false;
    }
    if (this->ry_max_speed != other.ry_max_speed) {
      return false;
    }
    if (this->rz_max_speed != other.rz_max_speed) {
      return false;
    }
    return true;
  }
  bool operator!=(const SixDofMotion_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SixDofMotion_Request_

// alias to use template instance with default allocator
using SixDofMotion_Request =
  promoc_assembly_interfaces::srv::SixDofMotion_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace promoc_assembly_interfaces


#ifndef _WIN32
# define DEPRECATED__promoc_assembly_interfaces__srv__SixDofMotion_Response __attribute__((deprecated))
#else
# define DEPRECATED__promoc_assembly_interfaces__srv__SixDofMotion_Response __declspec(deprecated)
#endif

namespace promoc_assembly_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct SixDofMotion_Response_
{
  using Type = SixDofMotion_Response_<ContainerAllocator>;

  explicit SixDofMotion_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->finished = false;
    }
  }

  explicit SixDofMotion_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->finished = false;
    }
  }

  // field types and members
  using _finished_type =
    bool;
  _finished_type finished;

  // setters for named parameter idiom
  Type & set__finished(
    const bool & _arg)
  {
    this->finished = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__promoc_assembly_interfaces__srv__SixDofMotion_Response
    std::shared_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__promoc_assembly_interfaces__srv__SixDofMotion_Response
    std::shared_ptr<promoc_assembly_interfaces::srv::SixDofMotion_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SixDofMotion_Response_ & other) const
  {
    if (this->finished != other.finished) {
      return false;
    }
    return true;
  }
  bool operator!=(const SixDofMotion_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SixDofMotion_Response_

// alias to use template instance with default allocator
using SixDofMotion_Response =
  promoc_assembly_interfaces::srv::SixDofMotion_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace promoc_assembly_interfaces

namespace promoc_assembly_interfaces
{

namespace srv
{

struct SixDofMotion
{
  using Request = promoc_assembly_interfaces::srv::SixDofMotion_Request;
  using Response = promoc_assembly_interfaces::srv::SixDofMotion_Response;
};

}  // namespace srv

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__SIX_DOF_MOTION__STRUCT_HPP_
