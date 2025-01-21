// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from promoc_assembly_interfaces:srv/ActivateXbots.idl
// generated code does not contain a copyright notice

#ifndef PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__STRUCT_HPP_
#define PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__promoc_assembly_interfaces__srv__ActivateXbots_Request __attribute__((deprecated))
#else
# define DEPRECATED__promoc_assembly_interfaces__srv__ActivateXbots_Request __declspec(deprecated)
#endif

namespace promoc_assembly_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct ActivateXbots_Request_
{
  using Type = ActivateXbots_Request_<ContainerAllocator>;

  explicit ActivateXbots_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->xbot_id = 0l;
      this->activation_status = false;
    }
  }

  explicit ActivateXbots_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->xbot_id = 0l;
      this->activation_status = false;
    }
  }

  // field types and members
  using _xbot_id_type =
    int32_t;
  _xbot_id_type xbot_id;
  using _activation_status_type =
    bool;
  _activation_status_type activation_status;

  // setters for named parameter idiom
  Type & set__xbot_id(
    const int32_t & _arg)
  {
    this->xbot_id = _arg;
    return *this;
  }
  Type & set__activation_status(
    const bool & _arg)
  {
    this->activation_status = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__promoc_assembly_interfaces__srv__ActivateXbots_Request
    std::shared_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__promoc_assembly_interfaces__srv__ActivateXbots_Request
    std::shared_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const ActivateXbots_Request_ & other) const
  {
    if (this->xbot_id != other.xbot_id) {
      return false;
    }
    if (this->activation_status != other.activation_status) {
      return false;
    }
    return true;
  }
  bool operator!=(const ActivateXbots_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct ActivateXbots_Request_

// alias to use template instance with default allocator
using ActivateXbots_Request =
  promoc_assembly_interfaces::srv::ActivateXbots_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace promoc_assembly_interfaces


#ifndef _WIN32
# define DEPRECATED__promoc_assembly_interfaces__srv__ActivateXbots_Response __attribute__((deprecated))
#else
# define DEPRECATED__promoc_assembly_interfaces__srv__ActivateXbots_Response __declspec(deprecated)
#endif

namespace promoc_assembly_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct ActivateXbots_Response_
{
  using Type = ActivateXbots_Response_<ContainerAllocator>;

  explicit ActivateXbots_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->activation_status = false;
    }
  }

  explicit ActivateXbots_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->activation_status = false;
    }
  }

  // field types and members
  using _activation_status_type =
    bool;
  _activation_status_type activation_status;

  // setters for named parameter idiom
  Type & set__activation_status(
    const bool & _arg)
  {
    this->activation_status = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__promoc_assembly_interfaces__srv__ActivateXbots_Response
    std::shared_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__promoc_assembly_interfaces__srv__ActivateXbots_Response
    std::shared_ptr<promoc_assembly_interfaces::srv::ActivateXbots_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const ActivateXbots_Response_ & other) const
  {
    if (this->activation_status != other.activation_status) {
      return false;
    }
    return true;
  }
  bool operator!=(const ActivateXbots_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct ActivateXbots_Response_

// alias to use template instance with default allocator
using ActivateXbots_Response =
  promoc_assembly_interfaces::srv::ActivateXbots_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace promoc_assembly_interfaces

namespace promoc_assembly_interfaces
{

namespace srv
{

struct ActivateXbots
{
  using Request = promoc_assembly_interfaces::srv::ActivateXbots_Request;
  using Response = promoc_assembly_interfaces::srv::ActivateXbots_Response;
};

}  // namespace srv

}  // namespace promoc_assembly_interfaces

#endif  // PROMOC_ASSEMBLY_INTERFACES__SRV__DETAIL__ACTIVATE_XBOTS__STRUCT_HPP_
