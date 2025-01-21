# generated from rosidl_generator_py/resource/_idl.py.em
# with input from promoc_assembly_interfaces:msg/XBotInfo.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_XBotInfo(type):
    """Metaclass of message 'XBotInfo'."""

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
                'promoc_assembly_interfaces.msg.XBotInfo')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__x_bot_info
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__x_bot_info
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__x_bot_info
            cls._TYPE_SUPPORT = module.type_support_msg__msg__x_bot_info
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__x_bot_info

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class XBotInfo(metaclass=Metaclass_XBotInfo):
    """Message class 'XBotInfo'."""

    __slots__ = [
        '_x_pos',
        '_y_pos',
        '_z_pos',
        '_rx_pos',
        '_ry_pos',
        '_rz_pos',
    ]

    _fields_and_field_types = {
        'x_pos': 'double',
        'y_pos': 'double',
        'z_pos': 'double',
        'rx_pos': 'double',
        'ry_pos': 'double',
        'rz_pos': 'double',
    }

    SLOT_TYPES = (
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
