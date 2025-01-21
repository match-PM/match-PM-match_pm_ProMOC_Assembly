// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from promoc_assembly_interfaces:srv/ArcMotion.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__STRUCT_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__promoc_assembly_interfaces__srv__ArcMotion_Request __attribute__((deprecated))
#else
# define DEPRECATED__promoc_assembly_interfaces__srv__ArcMotion_Request __declspec(deprecated)
#endif

namespace promoc_assembly_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct ArcMotion_Request_
{
  using Type = ArcMotion_Request_<ContainerAllocator>;

  explicit ArcMotion_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->xbot_id = 0l;
      this->arc_mode = 0l;
      this->arc_type = 0l;
      this->arc_dir = 0l;
      this->postion_mode = 0l;
      this->x_pos = 0.0;
      this->y_pos = 0.0;
      this->final_speed = 0.0;
      this->xy_max_speed = 0.0;
      this->xy_max_accl = 0.0;
      this->radius_meters = 0.0;
      this->angle_radians = 0.0;
    }
  }

  explicit ArcMotion_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->xbot_id = 0l;
      this->arc_mode = 0l;
      this->arc_type = 0l;
      this->arc_dir = 0l;
      this->postion_mode = 0l;
      this->x_pos = 0.0;
      this->y_pos = 0.0;
      this->final_speed = 0.0;
      this->xy_max_speed = 0.0;
      this->xy_max_accl = 0.0;
      this->radius_meters = 0.0;
      this->angle_radians = 0.0;
    }
  }

  // field types and members
  using _xbot_id_type =
    int32_t;
  _xbot_id_type xbot_id;
  using _arc_mode_type =
    int32_t;
  _arc_mode_type arc_mode;
  using _arc_type_type =
    int32_t;
  _arc_type_type arc_type;
  using _arc_dir_type =
    int32_t;
  _arc_dir_type arc_dir;
  using _postion_mode_type =
    int32_t;
  _postion_mode_type postion_mode;
  using _x_pos_type =
    double;
  _x_pos_type x_pos;
  using _y_pos_type =
    double;
  _y_pos_type y_pos;
  using _final_speed_type =
    double;
  _final_speed_type final_speed;
  using _xy_max_speed_type =
    double;
  _xy_max_speed_type xy_max_speed;
  using _xy_max_accl_type =
    double;
  _xy_max_accl_type xy_max_accl;
  using _radius_meters_type =
    double;
  _radius_meters_type radius_meters;
  using _angle_radians_type =
    double;
  _angle_radians_type angle_radians;

  // setters for named parameter idiom
  Type & set__xbot_id(
    const int32_t & _arg)
  {
    this->xbot_id = _arg;
    return *this;
  }
  Type & set__arc_mode(
    const int32_t & _arg)
  {
    this->arc_mode = _arg;
    return *this;
  }
  Type & set__arc_type(
    const int32_t & _arg)
  {
    this->arc_type = _arg;
    return *this;
  }
  Type & set__arc_dir(
    const int32_t & _arg)
  {
    this->arc_dir = _arg;
    return *this;
  }
  Type & set__postion_mode(
    const int32_t & _arg)
  {
    this->postion_mode = _arg;
    return *this;
  }
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
  Type & set__final_speed(
    const double & _arg)
  {
    this->final_speed = _arg;
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
  Type & set__radius_meters(
    const double & _arg)
  {
    this->radius_meters = _arg;
    return *this;
  }
  Type & set__angle_radians(
    const double & _arg)
  {
    this->angle_radians = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__promoc_assembly_interfaces__srv__ArcMotion_Request
    std::shared_ptr<promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__promoc_assembly_interfaces__srv__ArcMotion_Request
    std::shared_ptr<promoc_assembly_interfaces::srv::ArcMotion_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const ArcMotion_Request_ & other) const
  {
    if (this->xbot_id != other.xbot_id) {
      return false;
    }
    if (this->arc_mode != other.arc_mode) {
      return false;
    }
    if (this->arc_type != other.arc_type) {
      return false;
    }
    if (this->arc_dir != other.arc_dir) {
      return false;
    }
    if (this->postion_mode != other.postion_mode) {
      return false;
    }
    if (this->x_pos != other.x_pos) {
      return false;
    }
    if (this->y_pos != other.y_pos) {
      return false;
    }
    if (this->final_speed != other.final_speed) {
      return false;
    }
    if (this->xy_max_speed != other.xy_max_speed) {
      return false;
    }
    if (this->xy_max_accl != other.xy_max_accl) {
      return false;
    }
    if (this->radius_meters != other.radius_meters) {
      return false;
    }
    if (this->angle_radians != other.angle_radians) {
      return false;
    }
    return true;
  }
  bool operator!=(const ArcMotion_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct ArcMotion_Request_

// alias to use template instance with default allocator
using ArcMotion_Request =
  promoc_assembly_interfaces::srv::ArcMotion_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace promoc_assembly_interfaces


#ifndef _WIN32
# define DEPRECATED__promoc_assembly_interfaces__srv__ArcMotion_Response __attribute__((deprecated))
#else
# define DEPRECATED__promoc_assembly_interfaces__srv__ArcMotion_Response __declspec(deprecated)
#endif

namespace promoc_assembly_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct ArcMotion_Response_
{
  using Type = ArcMotion_Response_<ContainerAllocator>;

  explicit ArcMotion_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->structure_needs_at_least_one_member = 0;
    }
  }

  explicit ArcMotion_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->structure_needs_at_least_one_member = 0;
    }
  }

  // field types and members
  using _structure_needs_at_least_one_member_type =
    uint8_t;
  _structure_needs_at_least_one_member_type structure_needs_at_least_one_member;


  // constant declarations

  // pointer types
  using RawPtr =
    promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__promoc_assembly_interfaces__srv__ArcMotion_Response
    std::shared_ptr<promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__promoc_assembly_interfaces__srv__ArcMotion_Response
    std::shared_ptr<promoc_assembly_interfaces::srv::ArcMotion_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const ArcMotion_Response_ & other) const
  {
    if (this->structure_needs_at_least_one_member != other.structure_needs_at_least_one_member) {
      return false;
    }
    return true;
  }
  bool operator!=(const ArcMotion_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct ArcMotion_Response_

// alias to use template instance with default allocator
using ArcMotion_Response =
  promoc_assembly_interfaces::srv::ArcMotion_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace promoc_assembly_interfaces

namespace promoc_assembly_interfaces
{

namespace srv
{

struct ArcMotion
{
  using Request = promoc_assembly_interfaces::srv::ArcMotion_Request;
  using Response = promoc_assembly_interfaces::srv::ArcMotion_Response;
};

}  // namespace srv

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ARC_MOTION__STRUCT_HPP_
