# generated from rosidl_generator_py/resource/_idl.py.em
# with input from promoc_assembly_interfaces:srv/SixDofMotion.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_SixDofMotion_Request(type):
    """Metaclass of message 'SixDofMotion_Request'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('promoc_assembly_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'promoc_assembly_interfaces.srv.SixDofMotion_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__six_dof_motion__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__six_dof_motion__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__six_dof_motion__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__six_dof_motion__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__six_dof_motion__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class SixDofMotion_Request(metaclass=Metaclass_SixDofMotion_Request):
    """Message class 'SixDofMotion_Request'."""

    __slots__ = [
        '_x_pos',
        '_y_pos',
        '_z_pos',
        '_rx_pos',
        '_ry_pos',
        '_rz_pos',
        '_xy_max_speed',
        '_xy_max_accl',
        '_z_max_speed',
        '_rx_max_speed',
        '_ry_max_speed',
        '_rz_max_speed',
    ]

    _fields_and_field_types = {
        'x_pos': 'double',
        'y_pos': 'double',
        'z_pos': 'double',
        'rx_pos': 'double',
        'ry_pos': 'double',
        'rz_pos': 'double',
        'xy_max_speed': 'double',
        'xy_max_accl': 'double',
        'z_max_speed': 'double',
        'rx_max_speed': 'double',
        'ry_max_speed': 'double',
        'rz_max_speed': 'double',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.x_pos = kwargs.get('x_pos', float())
        self.y_pos = kwargs.get('y_pos', float())
        self.z_pos = kwargs.get('z_pos', float())
        self.rx_pos = kwargs.get('rx_pos', float())
        self.ry_pos = kwargs.get('ry_pos', float())
        self.rz_pos = kwargs.get('rz_pos', float())
        self.xy_max_speed = kwargs.get('xy_max_speed', float())
        self.xy_max_accl = kwargs.get('xy_max_accl', float())
        self.z_max_speed = kwargs.get('z_max_speed', float())
        self.rx_max_speed = kwargs.get('rx_max_speed', float())
        self.ry_max_speed = kwargs.get('ry_max_speed', float())
        self.rz_max_speed = kwargs.get('rz_max_speed', float())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.x_pos != other.x_pos:
            return False
        if self.y_pos != other.y_pos:
            return False
        if self.z_pos != other.z_pos:
            return False
        if self.rx_pos != other.rx_pos:
            return False
        if self.ry_pos != other.ry_pos:
            return False
        if self.rz_pos != other.rz_pos:
            return False
        if self.xy_max_speed != other.xy_max_speed:
            return False
        if self.xy_max_accl != other.xy_max_accl:
            return False
        if self.z_max_speed != other.z_max_speed:
            return False
        if self.rx_max_speed != other.rx_max_speed:
            return False
        if self.ry_max_speed != other.ry_max_speed:
            return False
        if self.rz_max_speed != other.rz_max_speed:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def x_pos(self):
        """Message field 'x_pos'."""
        return self._x_pos

    @x_pos.setter
    def x_pos(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'x_pos' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'x_pos' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._x_pos = value

    @builtins.property
    def y_pos(self):
        """Message field 'y_pos'."""
        return self._y_pos

    @y_pos.setter
    def y_pos(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'y_pos' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'y_pos' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._y_pos = value

    @builtins.property
    def z_pos(self):
        """Message field 'z_pos'."""
        return self._z_pos

    @z_pos.setter
    def z_pos(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'z_pos' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'z_pos' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._z_pos = value

    @builtins.property
    def rx_pos(self):
        """Message field 'rx_pos'."""
        return self._rx_pos

    @rx_pos.setter
    def rx_pos(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'rx_pos' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'rx_pos' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._rx_pos = value

    @builtins.property
    def ry_pos(self):
        """Message field 'ry_pos'."""
        return self._ry_pos

    @ry_pos.setter
    def ry_pos(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'ry_pos' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'ry_pos' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._ry_pos = value

    @builtins.property
    def rz_pos(self):
        """Message field 'rz_pos'."""
        return self._rz_pos

    @rz_pos.setter
    def rz_pos(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'rz_pos' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'rz_pos' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._rz_pos = value

    @builtins.property
    def xy_max_speed(self):
        """Message field 'xy_max_speed'."""
        return self._xy_max_speed

    @xy_max_speed.setter
    def xy_max_speed(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'xy_max_speed' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'xy_max_speed' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._xy_max_speed = value

    @builtins.property
    def xy_max_accl(self):
        """Message field 'xy_max_accl'."""
        return self._xy_max_accl

    @xy_max_accl.setter
    def xy_max_accl(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'xy_max_accl' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'xy_max_accl' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._xy_max_accl = value

    @builtins.property
    def z_max_speed(self):
        """Message field 'z_max_speed'."""
        return self._z_max_speed

    @z_max_speed.setter
    def z_max_speed(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'z_max_speed' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'z_max_speed' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._z_max_speed = value

    @builtins.property
    def rx_max_speed(self):
        """Message field 'rx_max_speed'."""
        return self._rx_max_speed

    @rx_max_speed.setter
    def rx_max_speed(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'rx_max_speed' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'rx_max_speed' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._rx_max_speed = value

    @builtins.property
    def ry_max_speed(self):
        """Message field 'ry_max_speed'."""
        return self._ry_max_speed

    @ry_max_speed.setter
    def ry_max_speed(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'ry_max_speed' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'ry_max_speed' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._ry_max_speed = value

    @builtins.property
    def rz_max_speed(self):
        """Message field 'rz_max_speed'."""
        return self._rz_max_speed

    @rz_max_speed.setter
    def rz_max_speed(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'rz_max_speed' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'rz_max_speed' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._rz_max_speed = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_SixDofMotion_Response(type):
    """Metaclass of message 'SixDofMotion_Response'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('promoc_assembly_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'promoc_assembly_interfaces.srv.SixDofMotion_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__six_dof_motion__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__six_dof_motion__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__six_dof_motion__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__six_dof_motion__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__six_dof_motion__response

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class SixDofMotion_Response(metaclass=Metaclass_SixDofMotion_Response):
    """Message class 'SixDofMotion_Response'."""

    __slots__ = [
        '_finished',
    ]

    _fields_and_field_types = {
        'finished': 'boolean',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.finished = kwargs.get('finished', bool())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.finished != other.finished:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def finished(self):
        """Message field 'finished'."""
        return self._finished

    @finished.setter
    def finished(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'finished' field must be of type 'bool'"
        self._finished = value


class Metaclass_SixDofMotion(type):
    """Metaclass of service 'SixDofMotion'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('promoc_assembly_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'promoc_assembly_interfaces.srv.SixDofMotion')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__six_dof_motion

            from promoc_assembly_interfaces.srv import _six_dof_motion
            if _six_dof_motion.Metaclass_SixDofMotion_Request._TYPE_SUPPORT is None:
                _six_dof_motion.Metaclass_SixDofMotion_Request.__import_type_support__()
            if _six_dof_motion.Metaclass_SixDofMotion_Response._TYPE_SUPPORT is None:
                _six_dof_motion.Metaclass_SixDofMotion_Response.__import_type_support__()


class SixDofMotion(metaclass=Metaclass_SixDofMotion):
    from promoc_assembly_interfaces.srv._six_dof_motion import SixDofMotion_Request as Request
    from promoc_assembly_interfaces.srv._six_dof_motion import SixDofMotion_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
