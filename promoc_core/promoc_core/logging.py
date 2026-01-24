"""
Structured Logging Utilities for ProMOC Assembly
=================================================

Provides consistent, tagged logging across all ProMOC packages.

Usage:
    from promoc_core.logging import TaggedLogger, LogTags

    class MyNode(Node):
        def __init__(self):
            super().__init__('my_node')
            self.log = TaggedLogger(self.get_logger(), LogTags.PMC_MOTION)
        
        def move(self):
            self.log.info("Moving to position...")  # [PMC:MOTION] Moving to position...
"""

from typing import Any


class LogTags:
    """Predefined log tags for consistent formatting across packages."""
    
    # Planar Motor
    PMC = "[PMC]"
    PMC_MOTION = "[PMC:MOTION]"
    PMC_CTRL = "[PMC:CTRL]"
    PMC_CONN = "[PMC:CONN]"
    
    # Linear Axis
    LTS = "[LTS]"
    LTS_MOVE = "[LTS:MOVE]"
    LTS_HOME = "[LTS:HOME]"
    LTS_CONN = "[LTS:CONN]"
    
    # Camera
    CAM = "[CAM]"
    CAM_AF = "[CAM:AF]"
    CAM_MTF = "[CAM:MTF]"
    CAM_IMG = "[CAM:IMG]"
    
    # System / Launch
    SYS = "[SYS]"
    LAUNCH = "[LAUNCH]"
    
    # Mock / Simulation
    MOCK = "[MOCK]"


class TaggedLogger:
    """
    Logger wrapper that prefixes all messages with a consistent tag.
    
    This ensures uniform log formatting across all packages and makes
    it easy to filter logs by component.
    
    Args:
        logger: The ROS2 logger instance (from node.get_logger())
        tag: The tag prefix (use LogTags constants)
    
    Example:
        >>> motion_log = TaggedLogger(self.get_logger(), LogTags.PMC_MOTION)
        >>> motion_log.info("XBot moving to target")
        # Output: [INFO] [node_name]: [PMC:MOTION] XBot moving to target
    """
    
    def __init__(self, logger: Any, tag: str):
        self._logger = logger
        self._tag = tag
    
    def _format(self, msg: str) -> str:
        """Format message with tag prefix."""
        return f"{self._tag} {msg}"
    
    def debug(self, msg: str) -> None:
        """Log a debug message."""
        self._logger.debug(self._format(msg))
    
    def info(self, msg: str) -> None:
        """Log an info message."""
        self._logger.info(self._format(msg))
    
    def warning(self, msg: str) -> None:
        """Log a warning message."""
        self._logger.warning(self._format(msg))
    
    def warn(self, msg: str) -> None:
        """Log a warning message (alias for warning)."""
        self.warning(msg)
    
    def error(self, msg: str) -> None:
        """Log an error message."""
        self._logger.error(self._format(msg))
    
    def fatal(self, msg: str) -> None:
        """Log a fatal message."""
        self._logger.fatal(self._format(msg))


def get_tagged_logger(node, tag: str) -> TaggedLogger:
    """
    Convenience function to create a TaggedLogger from a ROS2 node.
    
    Args:
        node: A ROS2 node instance
        tag: The tag prefix (use LogTags constants)
    
    Returns:
        A TaggedLogger instance
    
    Example:
        >>> from promoc_core.logging import get_tagged_logger, LogTags
        >>> self.log = get_tagged_logger(self, LogTags.LTS_MOVE)
    """
    return TaggedLogger(node.get_logger(), tag)
