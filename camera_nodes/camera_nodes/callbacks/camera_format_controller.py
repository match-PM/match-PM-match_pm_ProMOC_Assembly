"""Helpers for runtime camera format switching (ROI/Binning)."""

from __future__ import annotations

import time
from typing import Callable

from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, SetParameters


class CameraFormatController:
    """Encapsulates ROS parameter-based camera format changes."""

    PARAM_SET_SERVICES = (
        '/promoc/assembly_camera/set_parameters',
        '/promoc/assembly_camera_controller/set_parameters',
    )
    FORMAT_PARAM_NAME_VARIANTS = (
        {
            'width': 'Width',
            'height': 'Height',
            'offset_x': 'OffsetX',
            'offset_y': 'OffsetY',
            'bin_h': 'BinningHorizontal',
            'bin_v': 'BinningVertical',
        },
        {
            'width': 'ImageFormatControl.Width',
            'height': 'ImageFormatControl.Height',
            'offset_x': 'ImageFormatControl.OffsetX',
            'offset_y': 'ImageFormatControl.OffsetY',
            'bin_h': 'ImageFormatControl.BinningHorizontal',
            'bin_v': 'ImageFormatControl.BinningVertical',
        },
    )

    def __init__(self, node):
        self._node = node
        self._service_clients = {}

    def _get_service_clients(self, set_service: str):
        """Get cached set/get parameter clients for a service name."""
        cached = self._service_clients.get(set_service)
        if cached is not None:
            return cached

        get_service = set_service.replace('set_parameters', 'get_parameters')
        cached = {
            'set': self._node.create_client(SetParameters, set_service),
            'get': self._node.create_client(GetParameters, get_service),
            'set_service': set_service,
            'get_service': get_service,
        }
        self._service_clients[set_service] = cached
        return cached

    @staticmethod
    def _format_values(values: dict) -> str:
        """Format ROI/Binning values for compact diagnostics."""
        if not values:
            return 'n/a'
        width = values.get('width', '?')
        height = values.get('height', '?')
        offset_x = values.get('offset_x', '?')
        offset_y = values.get('offset_y', '?')
        bin_h = values.get('bin_h', '?')
        bin_v = values.get('bin_v', '?')
        return f'{width}x{height}, offset=({offset_x},{offset_y}), bin={bin_h}x{bin_v}'

    def _call_get_parameters(self, client, names, timeout_s: float = 2.0):
        req = GetParameters.Request()
        req.names = names
        future = client.call_async(req)
        start_wait = time.time()
        while not future.done() and time.time() - start_wait < timeout_s:
            time.sleep(0.05)
        if not future.done():
            return None
        return future.result()

    def _call_set_integer_parameter(self, client, name: str, value: int, timeout_s: float = 3.0):
        req = SetParameters.Request()
        req.parameters = [
            Parameter(
                name=name,
                value=ParameterValue(
                    type=ParameterType.PARAMETER_INTEGER,
                    integer_value=int(value),
                ),
            )
        ]
        future = client.call_async(req)
        start_wait = time.time()
        while not future.done() and time.time() - start_wait < timeout_s:
            time.sleep(0.05)
        if not future.done():
            return False, 'timeout while setting parameter'
        res = future.result()
        if not res or not res.results:
            return False, 'empty response from set_parameters'
        first = res.results[0]
        return bool(first.successful), str(first.reason)

    def _to_int(self, param_value):
        if param_value.type == ParameterType.PARAMETER_INTEGER:
            return int(param_value.integer_value)
        if param_value.type == ParameterType.PARAMETER_DOUBLE:
            return int(round(float(param_value.double_value)))
        return None

    def _get_float_param(self, name: str, default: float) -> float:
        if not self._node.has_parameter(name):
            return default
        value = self._node.get_parameter(name).value
        if value is None:
            return default
        return float(value)

    def _get_int_param(self, name: str, default: int) -> int:
        if not self._node.has_parameter(name):
            return default
        value = self._node.get_parameter(name).value
        if value is None:
            return default
        return int(value)

    def _get_bool_param(self, name: str, default: bool) -> bool:
        if not self._node.has_parameter(name):
            return default
        value = self._node.get_parameter(name).value
        if value is None:
            return default
        return bool(value)

    def _is_switch_logging_enabled(self) -> bool:
        return self._get_bool_param('mtf.log_format_switch', True)

    def read_state(self):
        """Read current ROI/Binning state from camera parameter services."""
        for set_service in self.PARAM_SET_SERVICES:
            clients = self._get_service_clients(set_service)
            set_client = clients['set']
            get_client = clients['get']
            if not set_client.wait_for_service(timeout_sec=0.5):
                continue
            if not get_client.wait_for_service(timeout_sec=0.5):
                continue

            for names in self.FORMAT_PARAM_NAME_VARIANTS:
                keys = list(names.keys())
                query_names = [names[k] for k in keys]
                res = self._call_get_parameters(get_client, query_names)
                if not res or not res.values or len(res.values) != len(query_names):
                    continue
                if all(v.type == ParameterType.PARAMETER_NOT_SET for v in res.values):
                    continue

                values = {}
                available_keys = set()
                for key, value_msg in zip(keys, res.values):
                    parsed = self._to_int(value_msg)
                    if parsed is not None:
                        values[key] = parsed
                        available_keys.add(key)

                if 'width' not in values or 'height' not in values:
                    continue

                return {
                    'set_service': set_service,
                    'names': names,
                    'values': values,
                    'available_keys': sorted(available_keys),
                }

        return None

    def set_format(self, state: dict, target_values: dict) -> bool:
        """Apply target ROI/Binning values via parameter service."""
        set_service = state.get('set_service')
        names = state.get('names', {})
        available_keys = set(state.get('available_keys', []))
        if not available_keys:
            # Backward compatibility with older state dicts.
            available_keys = set(names.keys())
        if not set_service or not names:
            return False

        clients = self._get_service_clients(set_service)
        set_client = clients['set']
        if not set_client.wait_for_service(timeout_sec=1.0):
            self._node.get_logger().warn(
                f'Parameter service not available for camera format switch: {set_service}'
            )
            return False

        has_bin_controls = (
            'bin_h' in available_keys and
            'bin_v' in available_keys and
            'bin_h' in target_values and
            'bin_v' in target_values
        )
        target_binning = target_values.get('bin_h') if has_bin_controls else None
        if target_binning is not None and int(target_binning) <= 1:
            write_order = ['bin_h', 'bin_v', 'offset_x', 'offset_y', 'width', 'height']
        elif target_binning is not None:
            write_order = ['offset_x', 'offset_y', 'width', 'height', 'bin_h', 'bin_v']
        else:
            write_order = ['offset_x', 'offset_y', 'width', 'height']

        write_keys = []
        for key in write_order:
            if key not in target_values or key not in names or key not in available_keys:
                continue
            write_keys.append(key)

        if self._is_switch_logging_enabled():
            optional_keys = {'offset_x', 'offset_y', 'bin_h', 'bin_v'}
            skipped_optional = [
                key for key in optional_keys
                if key in target_values and key in names and key not in write_keys
            ]
            if skipped_optional:
                self._node.get_logger().info(
                    f"Camera format switch: skipping unavailable optional keys {skipped_optional}"
                )

        for required in ('width', 'height'):
            if required in target_values and required not in write_keys:
                self._node.get_logger().error(
                    f"Required camera format key '{required}' is not available on parameter service."
                )
                return False

        if not write_keys:
            self._node.get_logger().warn(
                'No applicable camera format keys available for update; keeping current format.'
            )
            return True

        for key in write_keys:
            param_name = names[key]
            ok, reason = self._call_set_integer_parameter(
                set_client,
                param_name,
                int(target_values[key]),
            )
            if not ok:
                self._node.get_logger().error(
                    f'Failed to set {param_name}={target_values[key]}: {reason}'
                )
                return False

        return True

    def switch_to_full_frame_for_mtf(
        self,
        last_ts_ns: int,
        get_latest_image_fn: Callable[[], tuple],
        wait_for_new_image_fn: Callable[..., tuple],
    ):
        """Switch to full frame before MTF and return (restore_state, new_image)."""
        if getattr(self._node, 'use_simulator', False):
            return None, None
        if not self._get_bool_param('mtf.use_full_frame', False):
            return None, None

        state = self.read_state()
        if state is None:
            self._node.get_logger().warn(
                'Could not read current camera ROI/Binning state. '
                'Proceeding with current image for MTF.'
            )
            return None, None

        current = dict(state.get('values', {}))
        restore_state = {
            'set_service': state.get('set_service'),
            'names': dict(state.get('names', {})),
            'values': current,
            'available_keys': list(state.get('available_keys', [])),
        }

        full_w_default = int(current.get('width', 5536))
        full_h_default = int(current.get('height', 3692))
        target = {
            'width': self._get_int_param('mtf.full_frame_width', full_w_default),
            'height': self._get_int_param('mtf.full_frame_height', full_h_default),
            'offset_x': self._get_int_param('mtf.full_frame_offset_x', 0),
            'offset_y': self._get_int_param('mtf.full_frame_offset_y', 0),
            'bin_h': self._get_int_param('mtf.full_frame_binning', 1),
            'bin_v': self._get_int_param('mtf.full_frame_binning', 1),
        }
        if self._is_switch_logging_enabled():
            self._node.get_logger().info(
                f"MTF format switch start: current={self._format_values(current)} "
                f"target={self._format_values(target)}"
            )

        if not self.set_format(state, target):
            self._node.get_logger().warn(
                'Failed to switch camera to full frame. '
                'Proceeding with current image for MTF.'
            )
            return None, None

        settle_s = self._get_float_param('mtf.full_frame_settle_s', 0.25)
        if settle_s > 0:
            time.sleep(settle_s)

        timeout_s = self._get_float_param('mtf.full_frame_image_timeout_s', 2.0)
        new_image, _ = wait_for_new_image_fn(last_ts_ns, timeout=timeout_s)
        if new_image is None:
            new_image, _ = get_latest_image_fn()

        if self._is_switch_logging_enabled():
            applied_state = self.read_state()
            if applied_state:
                applied_values = applied_state.get('values', {})
                self._node.get_logger().info(
                    f"MTF format switch applied: actual={self._format_values(applied_values)} "
                    f"service={applied_state.get('set_service', '?')}"
                )
            else:
                self._node.get_logger().warn(
                    'MTF format switch verification unavailable: failed to read back camera state.'
                )
            if new_image is not None:
                img_h, img_w = new_image.shape[:2]
                self._node.get_logger().info(
                    f'MTF format switch image: {img_w}x{img_h}'
                )
            else:
                self._node.get_logger().warn(
                    'MTF format switch image unavailable after switch; using latest cached image.'
                )

        return restore_state, new_image

    def restore_after_mtf(self, restore_state: dict):
        """Restore camera ROI/Binning after MTF measurement."""
        if not restore_state or getattr(self._node, 'use_simulator', False):
            return
        if not self._get_bool_param('mtf.restore_after_measurement', True):
            return

        target = dict(restore_state.get('values', {}))
        if not target:
            return
        if self._is_switch_logging_enabled():
            self._node.get_logger().info(
                f"MTF format restore start: target={self._format_values(target)}"
            )

        if not self.set_format(restore_state, target):
            self._node.get_logger().warn('Failed to restore camera ROI/Binning after MTF.')
            return

        settle_s = self._get_float_param('mtf.restore_settle_s', 0.15)
        if settle_s > 0:
            time.sleep(settle_s)
        if self._is_switch_logging_enabled():
            restored_state = self.read_state()
            if restored_state:
                self._node.get_logger().info(
                    f"MTF format restore applied: actual={self._format_values(restored_state.get('values', {}))} "
                    f"service={restored_state.get('set_service', '?')}"
                )
            else:
                self._node.get_logger().warn(
                    'MTF format restore verification unavailable: failed to read back camera state.'
                )
