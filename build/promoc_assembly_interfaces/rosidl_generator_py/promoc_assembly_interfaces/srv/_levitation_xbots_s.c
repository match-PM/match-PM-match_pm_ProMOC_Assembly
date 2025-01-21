// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from promoc_assembly_interfaces:srv/LevitationXbots.idl
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
#include "promoc_assembly_interfaces/srv/detail/levitation_xbots__struct.h"
#include "promoc_assembly_interfaces/srv/detail/levitation_xbots__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool promoc_assembly_interfaces__srv__levitation_xbots__request__convert_from_py(PyObject * _pymsg, void * _ros_message)
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
    assert(strncmp("promoc_assembly_interfaces.srv._levitation_xbots.LevitationXbots_Request", full_classname_dest, 72) == 0);
  }
  promoc_assembly_interfaces__srv__LevitationXbots_Request * ros_message = _ros_message;
  {  // xbot_id
    PyObject * field = PyObject_GetAttrString(_pymsg, "xbot_id");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->xbot_id = (int32_t)PyLong_AsLong(field);
    Py_DECREF(field);
  }
  {  // levitation
    PyObject * field = PyObject_GetAttrString(_pymsg, "levitation");
    if (!field) {
      return false;
    }
    assert(PyBool_Check(field));
    ros_message->levitation = (Py_True == field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * promoc_assembly_interfaces__srv__levitation_xbots__request__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of LevitationXbots_Request */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("promoc_assembly_interfaces.srv._levitation_xbots");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "LevitationXbots_Request");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  promoc_assembly_interfaces__srv__LevitationXbots_Request * ros_message = (promoc_assembly_interfaces__srv__LevitationXbots_Request *)raw_ros_message;
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
  {  // levitation
    PyObject * field = NULL;
    field = PyBool_FromLong(ros_message->levitation ? 1 : 0);
    {
      int rc = PyObject_SetAttrString(_pymessage, "levitation", field);
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
// #include "promoc_assembly_interfaces/srv/detail/levitation_xbots__struct.h"
// already included above
// #include "promoc_assembly_interfaces/srv/detail/levitation_xbots__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool promoc_assembly_interfaces__srv__levitation_xbots__response__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[74];
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
    assert(strncmp("promoc_assembly_interfaces.srv._levitation_xbots.LevitationXbots_Response", full_classname_dest, 73) == 0);
  }
  promoc_assembly_interfaces__srv__LevitationXbots_Response * ros_message = _ros_message;
  {  // levitation
    PyObject * field = PyObject_GetAttrString(_pymsg, "levitation");
    if (!field) {
      return false;
    }
    assert(PyBool_Check(field));
    ros_message->levitation = (Py_True == field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * promoc_assembly_interfaces__srv__levitation_xbots__response__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of LevitationXbots_Response */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("promoc_assembly_interfaces.srv._levitation_xbots");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "LevitationXbots_Response");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  promoc_assembly_interfaces__srv__LevitationXbots_Response * ros_message = (promoc_assembly_interfaces__srv__LevitationXbots_Response *)raw_ros_message;
  {  // levitation
    PyObject * field = NULL;
    field = PyBool_FromLong(ros_message->levitation ? 1 : 0);
    {
      int rc = PyObject_SetAttrString(_pymessage, "levitation", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}
