# generated from rosidl_generator_py/resource/_idl.py.em
# with input from promoc_assembly_interfaces:srv/ActivateXbots.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_ActivateXbots_Request(type):
    """Metaclass of message 'ActivateXbots_Request'."""

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
                'promoc_assembly_interfaces.srv.ActivateXbots_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__activate_xbots__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__activate_xbots__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__activate_xbots__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__activate_xbots__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__activate_xbots__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class ActivateXbots_Request(metaclass=Metaclass_ActivateXbots_Request):
    """Message class 'ActivateXbots_Request'."""

    __slots__ = [
        '_xbot_id',
        '_activation_status',
    ]

    _fields_and_field_types = {
        'xbot_id': 'int32',
        'activation_status': 'boolean',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.xbot_id = kwargs.get('xbot_id', int())
        self.activation_status = kwargs.get('activation_status', bool())

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
        if self.activation_status != other.activation_status:
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
    def activation_status(self):
        """Message field 'activation_status'."""
        return self._activation_status

    @activation_status.setter
    def activation_status(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'activation_status' field must be of type 'bool'"
        self._activation_status = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_ActivateXbots_Response(type):
    """Metaclass of message 'ActivateXbots_Response'."""

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
                'promoc_assembly_interfaces.srv.ActivateXbots_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__activate_xbots__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__activate_xbots__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__activate_xbots__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__activate_xbots__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__activate_xbots__response

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class ActivateXbots_Response(metaclass=Metaclass_ActivateXbots_Response):
    """Message class 'ActivateXbots_Response'."""

    __slots__ = [
        '_activation_status',
    ]

    _fields_and_field_types = {
        'activation_status': 'boolean',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.activation_status = kwargs.get('activation_status', bool())

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
        if self.activation_status != other.activation_status:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def activation_status(self):
        """Message field 'activation_status'."""
        return self._activation_status

    @activation_status.setter
    def activation_status(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'activation_status' field must be of type 'bool'"
        self._activation_status = value


class Metaclass_ActivateXbots(type):
    """Metaclass of service 'ActivateXbots'."""

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
                'promoc_assembly_interfaces.srv.ActivateXbots')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__activate_xbots

            from promoc_assembly_interfaces.srv import _activate_xbots
            if _activate_xbots.Metaclass_ActivateXbots_Request._TYPE_SUPPORT is None:
                _activate_xbots.Metaclass_ActivateXbots_Request.__import_type_support__()
            if _activate_xbots.Metaclass_ActivateXbots_Response._TYPE_SUPPORT is None:
                _activate_xbots.Metaclass_ActivateXbots_Response.__import_type_support__()


class ActivateXbots(metaclass=Metaclass_ActivateXbots):
    from promoc_assembly_interfaces.srv._activate_xbots import ActivateXbots_Request as Request
    from promoc_assembly_interfaces.srv._activate_xbots import ActivateXbots_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
