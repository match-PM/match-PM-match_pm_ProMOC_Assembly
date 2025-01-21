// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from promoc_assembly_interfaces:srv/LinearMotionSi.idl
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
#include "promoc_assembly_interfaces/srv/detail/linear_motion_si__struct.h"
#include "promoc_assembly_interfaces/srv/detail/linear_motion_si__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool promoc_assembly_interfaces__srv__linear_motion_si__request__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[72];
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
    assert(strncmp("promoc_assembly_interfaces.srv._linear_motion_si.LinearMotionSi_Request", full_classname_dest, 71) == 0);
  }
  promoc_assembly_interfaces__srv__LinearMotionSi_Request * ros_message = _ros_message;
  {  // xbot_id
    PyObject * field = PyObject_GetAttrString(_pymsg, "xbot_id");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->xbot_id = (int32_t)PyLong_AsLong(field);
    Py_DECREF(field);
  }
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

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * promoc_assembly_interfaces__srv__linear_motion_si__request__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of LinearMotionSi_Request */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("promoc_assembly_interfaces.srv._linear_motion_si");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "LinearMotionSi_Request");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  promoc_assembly_interfaces__srv__LinearMotionSi_Request * ros_message = (promoc_assembly_interfaces__srv__LinearMotionSi_Request *)raw_ros_message;
  {  // xbot_id
    PyObject * field = NULL;
    field = PyLong_FromLong(ros_message->xbot_id);
    {
      int rc = PyObject_SetAttrString(_pymessage, "xbot_id", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
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
// #include "promoc_assembly_interfaces/srv/detail/linear_motion_si__struct.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/linear_motion_si__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool promoc_assembly_interfaces__srv__linear_motion_si__response__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[73];
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
    assert(strncmp("promoc_assembly_interfaces.srv._linear_motion_si.LinearMotionSi_Response", full_classname_dest, 72) == 0);
  }
  promoc_assembly_interfaces__srv__LinearMotionSi_Response * ros_message = _ros_message;
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
PyObject * promoc_assembly_interfaces__srv__linear_motion_si__response__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of LinearMotionSi_Response */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("promoc_assembly_interfaces.srv._linear_motion_si");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "LinearMotionSi_Response");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  promoc_assembly_interfaces__srv__LinearMotionSi_Response * ros_message = (promoc_assembly_interfaces__srv__LinearMotionSi_Response *)raw_ros_message;
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
