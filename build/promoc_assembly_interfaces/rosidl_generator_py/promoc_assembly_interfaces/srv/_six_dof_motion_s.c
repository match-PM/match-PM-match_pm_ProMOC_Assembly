// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from promoc_assembly_interfaces:srv/SixDofMotion.idl
// generated code does not contain a copyright notice
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <Python.h>
#include <stdbool.h>
#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-function"
#endif
#include "numpy/ndarrayobject.h"
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif
#include "rosidl_runtime_c/visibility_control.h"
#include "promoc_assembly_interfaces/srv/detail/six_dof_motion__struct.h"
#include "promoc_assembly_interfaces/srv/detail/six_dof_motion__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool promoc_assembly_interfaces__srv__six_dof_motion__request__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[68];
    {
      char * class_name = NULL;
      char * module_name = NULL;
      {
        PyObject * class_attr = PyObject_GetAttrString(_pymsg, "__class__");
        if (class_attr) {
          PyObject * name_attr = PyObject_GetAttrString(class_attr, "__name__");
          if (name_attr) {
            class_name = (char *)PyUnicode_1BYTE_DATA(name_attr);
            Py_DECREF(name_attr);
          }
          PyObject * module_attr = PyObject_GetAttrString(class_attr, "__module__");
          if (module_attr) {
            module_name = (char *)PyUnicode_1BYTE_DATA(module_attr);
            Py_DECREF(module_attr);
          }
          Py_DECREF(class_attr);
        }
      }
      if (!class_name || !module_name) {
        return false;
      }
      snprintf(full_classname_dest, sizeof(full_classname_dest), "%s.%s", module_name, class_name);
    }
    assert(strncmp("promoc_assembly_interfaces.srv._six_dof_motion.SixDofMotion_Request", full_classname_dest, 67) == 0);
  }
  promoc_assembly_interfaces__srv__SixDofMotion_Request * ros_message = _ros_message;
  {  // x_pos
    PyObject * field = PyObject_GetAttrString(_pymsg, "x_pos");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->x_pos = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // y_pos
    PyObject * field = PyObject_GetAttrString(_pymsg, "y_pos");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->y_pos = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // z_pos
    PyObject * field = PyObject_GetAttrString(_pymsg, "z_pos");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->z_pos = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // rx_pos
    PyObject * field = PyObject_GetAttrString(_pymsg, "rx_pos");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->rx_pos = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // ry_pos
    PyObject * field = PyObject_GetAttrString(_pymsg, "ry_pos");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->ry_pos = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // rz_pos
    PyObject * field = PyObject_GetAttrString(_pymsg, "rz_pos");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->rz_pos = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // xy_max_speed
    PyObject * field = PyObject_GetAttrString(_pymsg, "xy_max_speed");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->xy_max_speed = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // xy_max_accl
    PyObject * field = PyObject_GetAttrString(_pymsg, "xy_max_accl");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->xy_max_accl = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // z_max_speed
    PyObject * field = PyObject_GetAttrString(_pymsg, "z_max_speed");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->z_max_speed = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // rx_max_speed
    PyObject * field = PyObject_GetAttrString(_pymsg, "rx_max_speed");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->rx_max_speed = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // ry_max_speed
    PyObject * field = PyObject_GetAttrString(_pymsg, "ry_max_speed");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->ry_max_speed = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // rz_max_speed
    PyObject * field = PyObject_GetAttrString(_pymsg, "rz_max_speed");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->rz_max_speed = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * promoc_assembly_interfaces__srv__six_dof_motion__request__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of SixDofMotion_Request */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("promoc_assembly_interfaces.srv._six_dof_motion");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "SixDofMotion_Request");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  promoc_assembly_interfaces__srv__SixDofMotion_Request * ros_message = (promoc_assembly_interfaces__srv__SixDofMotion_Request *)raw_ros_message;
  {  // x_pos
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->x_pos);
    {
      int rc = PyObject_SetAttrString(_pymessage, "x_pos", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // y_pos
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->y_pos);
    {
      int rc = PyObject_SetAttrString(_pymessage, "y_pos", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // z_pos
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->z_pos);
    {
      int rc = PyObject_SetAttrString(_pymessage, "z_pos", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // rx_pos
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->rx_pos);
    {
      int rc = PyObject_SetAttrString(_pymessage, "rx_pos", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // ry_pos
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->ry_pos);
    {
      int rc = PyObject_SetAttrString(_pymessage, "ry_pos", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // rz_pos
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->rz_pos);
    {
      int rc = PyObject_SetAttrString(_pymessage, "rz_pos", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // xy_max_speed
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->xy_max_speed);
    {
      int rc = PyObject_SetAttrString(_pymessage, "xy_max_speed", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // xy_max_accl
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->xy_max_accl);
    {
      int rc = PyObject_SetAttrString(_pymessage, "xy_max_accl", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // z_max_speed
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->z_max_speed);
    {
      int rc = PyObject_SetAttrString(_pymessage, "z_max_speed", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // rx_max_speed
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->rx_max_speed);
    {
      int rc = PyObject_SetAttrString(_pymessage, "rx_max_speed", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // ry_max_speed
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->ry_max_speed);
    {
      int rc = PyObject_SetAttrString(_pymessage, "ry_max_speed", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // rz_max_speed
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->rz_max_speed);
    {
      int rc = PyObject_SetAttrString(_pymessage, "rz_max_speed", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
// already included above
// #include <Python.h>
// already included above
// #include <stdbool.h>
// already included above
// #include "numpy/ndarrayobject.h"
// already included above
// #include "rosidl_runtime_c/visibility_control.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/six_dof_motion__struct.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/six_dof_motion__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool promoc_assembly_interfaces__srv__six_dof_motion__response__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[69];
    {
      char * class_name = NULL;
      char * module_name = NULL;
      {
        PyObject * class_attr = PyObject_GetAttrString(_pymsg, "__class__");
        if (class_attr) {
          PyObject * name_attr = PyObject_GetAttrString(class_attr, "__name__");
          if (name_attr) {
            class_name = (char *)PyUnicode_1BYTE_DATA(name_attr);
            Py_DECREF(name_attr);
          }
          PyObject * module_attr = PyObject_GetAttrString(class_attr, "__module__");
          if (module_attr) {
            module_name = (char *)PyUnicode_1BYTE_DATA(module_attr);
            Py_DECREF(module_attr);
          }
          Py_DECREF(class_attr);
        }
      }
      if (!class_name || !module_name) {
        return false;
      }
      snprintf(full_classname_dest, sizeof(full_classname_dest), "%s.%s", module_name, class_name);
    }
    assert(strncmp("promoc_assembly_interfaces.srv._six_dof_motion.SixDofMotion_Response", full_classname_dest, 68) == 0);
  }
  promoc_assembly_interfaces__srv__SixDofMotion_Response * ros_message = _ros_message;
  {  // finished
    PyObject * field = PyObject_GetAttrString(_pymsg, "finished");
    if (!field) {
      return false;
    }
    assert(PyBool_Check(field));
    ros_message->finished = (Py_True == field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * promoc_assembly_interfaces__srv__six_dof_motion__response__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of SixDofMotion_Response */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("promoc_assembly_interfaces.srv._six_dof_motion");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "SixDofMotion_Response");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  promoc_assembly_interfaces__srv__SixDofMotion_Response * ros_message = (promoc_assembly_interfaces__srv__SixDofMotion_Response *)raw_ros_message;
  {  // finished
    PyObject * field = NULL;
    field = PyBool_FromLong(ros_message->finished ? 1 : 0);
    {
      int rc = PyObject_SetAttrString(_pymessage, "finished", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}
