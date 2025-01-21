# generated from rosidl_generator_py/resource/_idl.py.em
# with input from promoc_assembly_interfaces:srv/ArcMotion.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_ArcMotion_Request(type):
    """Metaclass of message 'ArcMotion_Request'."""

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
                'promoc_assembly_interfaces.srv.ArcMotion_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__arc_motion__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__arc_motion__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__arc_motion__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__arc_motion__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__arc_motion__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class ArcMotion_Request(metaclass=Metaclass_ArcMotion_Request):
    """Message class 'ArcMotion_Request'."""

    __slots__ = [
        '_xbot_id',
        '_arc_mode',
        '_arc_type',
        '_arc_dir',
        '_postion_mode',
        '_x_pos',
        '_y_pos',
        '_final_speed',
        '_xy_max_speed',
        '_xy_max_accl',
        '_radius_meters',
        '_angle_radians',
    ]

    _fields_and_field_types = {
        'xbot_id': 'int32',
        'arc_mode': 'int32',
        'arc_type': 'int32',
        'arc_dir': 'int32',
        'postion_mode': 'int32',
        'x_pos': 'double',
        'y_pos': 'double',
        'final_speed': 'double',
        'xy_max_speed': 'double',
        'xy_max_accl': 'double',
        'radius_meters': 'double',
        'angle_radians': 'double',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
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
        self.xbot_id = kwargs.get('xbot_id', int())
        self.arc_mode = kwargs.get('arc_mode', int())
        self.arc_type = kwargs.get('arc_type', int())
        self.arc_dir = kwargs.get('arc_dir', int())
        self.postion_mode = kwargs.get('postion_mode', int())
        self.x_pos = kwargs.get('x_pos', float())
        self.y_pos = kwargs.get('y_pos', float())
        self.final_speed = kwargs.get('final_speed', float())
        self.xy_max_speed = kwargs.get('xy_max_speed', float())
        self.xy_max_accl = kwargs.get('xy_max_accl', float())
        self.radius_meters = kwargs.get('radius_meters', float())
        self.angle_radians = kwargs.get('angle_radians', float())

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
        if self.xbot_id != other.xbot_id:
            return False
        if self.arc_mode != other.arc_mode:
            return False
        if self.arc_type != other.arc_type:
            return False
        if self.arc_dir != other.arc_dir:
            return False
        if self.postion_mode != other.postion_mode:
            return False
        if self.x_pos != other.x_pos:
            return False
        if self.y_pos != other.y_pos:
            return False
        if self.final_speed != other.final_speed:
            return False
        if self.xy_max_speed != other.xy_max_speed:
            return False
        if self.xy_max_accl != other.xy_max_accl:
            return False
        if self.radius_meters != other.radius_meters:
            return False
        if self.angle_radians != other.angle_radians:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def xbot_id(self):
        """Message field 'xbot_id'."""
        return self._xbot_id

    @xbot_id.setter
    def xbot_id(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'xbot_id' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'xbot_id' field must be an integer in [-2147483648, 2147483647]"
        self._xbot_id = value

    @builtins.property
    def arc_mode(self):
        """Message field 'arc_mode'."""
        return self._arc_mode

    @arc_mode.setter
    def arc_mode(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'arc_mode' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'arc_mode' field must be an integer in [-2147483648, 2147483647]"
        self._arc_mode = value

    @builtins.property
    def arc_type(self):
        """Message field 'arc_type'."""
        return self._arc_type

    @arc_type.setter
    def arc_type(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'arc_type' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'arc_type' field must be an integer in [-2147483648, 2147483647]"
        self._arc_type = value

    @builtins.property
    def arc_dir(self):
        """Message field 'arc_dir'."""
        return self._arc_dir

    @arc_dir.setter
    def arc_dir(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'arc_dir' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'arc_dir' field must be an integer in [-2147483648, 2147483647]"
        self._arc_dir = value

    @builtins.property
    def postion_mode(self):
        """Message field 'postion_mode'."""
        return self._postion_mode

    @postion_mode.setter
    def postion_mode(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'postion_mode' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'postion_mode' field must be an integer in [-2147483648, 2147483647]"
        self._postion_mode = value

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
    def final_speed(self):
        """Message field 'final_speed'."""
        return self._final_speed

    @final_speed.setter
    def final_speed(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'final_speed' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'final_speed' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._final_speed = value

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
    def radius_meters(self):
        """Message field 'radius_meters'."""
        return self._radius_meters

    @radius_meters.setter
    def radius_meters(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'radius_meters' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'radius_meters' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._radius_meters = value

    @builtins.property
    def angle_radians(self):
        """Message field 'angle_radians'."""
        return self._angle_radians

    @angle_radians.setter
    def angle_radians(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'angle_radians' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'angle_radians' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._angle_radians = value


# Import statements for member types

# already imported above
# import rosidl_parser.definition


class Metaclass_ArcMotion_Response(type):
    """Metaclass of message 'ArcMotion_Response'."""

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
                'promoc_assembly_interfaces.srv.ArcMotion_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__arc_motion__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__arc_motion__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__arc_motion__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__arc_motion__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__arc_motion__response

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class ArcMotion_Response(metaclass=Metaclass_ArcMotion_Response):
    """Message class 'ArcMotion_Response'."""

    __slots__ = [
    ]

    _fields_and_field_types = {
    }

    SLOT_TYPES = (
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))

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
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)


class Metaclass_ArcMotion(type):
    """Metaclass of service 'ArcMotion'."""

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
                'promoc_assembly_interfaces.srv.ArcMotion')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__arc_motion

            from promoc_assembly_interfaces.srv import _arc_motion
            if _arc_motion.Metaclass_ArcMotion_Request._TYPE_SUPPORT is None:
                _arc_motion.Metaclass_ArcMotion_Request.__import_type_support__()
            if _arc_motion.Metaclass_ArcMotion_Response._TYPE_SUPPORT is None:
                _arc_motion.Metaclass_ArcMotion_Response.__import_type_support__()


class ArcMotion(metaclass=Metaclass_ArcMotion):
    from promoc_assembly_interfaces.srv._arc_motion import ArcMotion_Request as Request
    from promoc_assembly_interfaces.srv._arc_motion import ArcMotion_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
