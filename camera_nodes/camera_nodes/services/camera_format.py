"""Helpers for runtime camera format switching (ROI/Binning)."""

from __future__ import annotations

import json
import time
from typing import Callable

from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, ListParameters, SetParameters

from .base import ParameterAccessor


class CameraFormatController:
    """Encapsulates ROS parameter-based camera format changes."""
    FORMAT_QUERY_GROUPS = (
        ("width", "height"),
        ("offset_x", "offset_y"),
        ("bin_h", "bin_v"),
    )
    CAPTURE_QUERY_GROUPS = FORMAT_QUERY_GROUPS + (
        ("pixel_format",),
        ("exposure_time",),
        ("gain",),
        ("exposure_auto",),
        ("gain_auto",),
        ("white_balance_auto",),
        ("gamma",),
    )
    FORMAT_PARAM_NAME_VARIANTS = (
        {
            "width": "Width",
            "height": "Height",
            "offset_x": "OffsetX",
            "offset_y": "OffsetY",
            "bin_h": "BinningHorizontal",
            "bin_v": "BinningVertical",
        },
        {
            "width": "ImageFormatControl.Width",
            "height": "ImageFormatControl.Height",
            "offset_x": "ImageFormatControl.OffsetX",
            "offset_y": "ImageFormatControl.OffsetY",
            "bin_h": "ImageFormatControl.BinningHorizontal",
            "bin_v": "ImageFormatControl.BinningVertical",
        },
    )
    CAPTURE_PARAM_NAME_VARIANTS = (
        {
            "width": "Width",
            "height": "Height",
            "offset_x": "OffsetX",
            "offset_y": "OffsetY",
            "bin_h": "BinningHorizontal",
            "bin_v": "BinningVertical",
            "pixel_format": "PixelFormat",
            "exposure_time": "ExposureTime",
            "gain": "Gain",
            "exposure_auto": "ExposureAuto",
            "gain_auto": "GainAuto",
            "white_balance_auto": "BalanceWhiteAuto",
            "gamma": "Gamma",
            "gamma_enable": "GammaEnable",
            "color_transform_enable": "ColorTransformationEnable",
        },
        {
            "width": "ImageFormatControl.Width",
            "height": "ImageFormatControl.Height",
            "offset_x": "ImageFormatControl.OffsetX",
            "offset_y": "ImageFormatControl.OffsetY",
            "bin_h": "ImageFormatControl.BinningHorizontal",
            "bin_v": "ImageFormatControl.BinningVertical",
            "pixel_format": "ImageFormatControl.PixelFormat",
            "exposure_time": "AcquisitionControl.ExposureTime",
            "gain": "AnalogControl.Gain",
            "exposure_auto": "AcquisitionControl.ExposureAuto",
            "gain_auto": "AnalogControl.GainAuto",
            "white_balance_auto": "ColorControl.BalanceWhiteAuto",
            "gamma": "AnalogControl.Gamma",
            "gamma_enable": "AnalogControl.GammaEnable",
            "color_transform_enable": "ColorTransformationControl.ColorTransformationEnable",
        },
    )
    SCIENTIFIC_CAPTURE_VERIFY_KEYS = (
        "pixel_format",
        "bin_h",
        "bin_v",
        "exposure_time",
        "gain",
        "exposure_auto",
        "gain_auto",
        "white_balance_auto",
        "gamma_enable",
        "color_transform_enable",
    )

    @staticmethod
    def _failure_reason_rank(reason: str) -> int:
        """Prefer root-cause diagnostics over generic service-unavailable fallbacks."""
        text = str(reason or "")
        if "missing width/height" in text:
            return 40
        if "all queried format params not-set" in text:
            return 30
        if "empty/incomplete get_parameters response" in text:
            return 20
        if "get service unavailable" in text:
            return 10
        if "set service unavailable" in text:
            return 0
        return 5

    def __init__(self, node):
        self._node = node
        self._service_clients = {}
        self.params = ParameterAccessor(node)
        self._last_capture_state = None
        self._last_operation_error = ""
        self._configured_declared_parameter_names = None

    def _param_set_services(self) -> tuple[str, ...]:
        """Return configured parameter-service candidates in priority order."""
        primary = self.params.as_str(
            "camera.param_set_service_primary",
            "/promoc/promoc_camera/set_parameters",
        ).strip()
        secondary = self.params.as_str(
            "camera.param_set_service_secondary",
            "/promoc/promoc_camera_controller/set_parameters",
        ).strip()
        return tuple(service for service in (primary, secondary) if service)

    def _get_service_clients(self, set_service: str):
        """Get cached set/get parameter clients for a service name."""
        cached = self._service_clients.get(set_service)
        if cached is not None:
            return cached

        get_service = set_service.replace("set_parameters", "get_parameters")
        list_service = set_service.replace("set_parameters", "list_parameters")
        cached = {
            "set": self._node.create_client(SetParameters, set_service),
            "get": self._node.create_client(GetParameters, get_service),
            "list": self._node.create_client(ListParameters, list_service),
            "set_service": set_service,
            "get_service": get_service,
            "list_service": list_service,
            "declared_param_names": None,
        }
        self._service_clients[set_service] = cached
        return cached

    @staticmethod
    def _format_exposure_us(exposure_time) -> str:
        """Format exposure readback in microseconds and milliseconds."""
        try:
            exposure_us = float(exposure_time)
        except (TypeError, ValueError):
            return str(exposure_time)
        exposure_ms = exposure_us / 1000.0
        return f"{exposure_us:.1f}us/{exposure_ms:.3f}ms"

    @staticmethod
    def _format_values(values: dict) -> str:
        """Format ROI/Binning values for compact diagnostics."""
        if not values:
            return "n/a"
        width = values.get("width", "?")
        height = values.get("height", "?")
        offset_x = values.get("offset_x", "?")
        offset_y = values.get("offset_y", "?")
        bin_h = values.get("bin_h", "?")
        bin_v = values.get("bin_v", "?")
        pixel_format = values.get("pixel_format")
        gain = values.get("gain")
        exposure_time = values.get("exposure_time")
        extra = []
        if pixel_format not in (None, ""):
            extra.append(f"pixfmt={pixel_format}")
        if exposure_time is not None:
            extra.append(f"exp={CameraFormatController._format_exposure_us(exposure_time)}")
        if gain is not None:
            extra.append(f"gain={gain}")
        extra_text = f", {' '.join(extra)}" if extra else ""
        return (
            f"{width}x{height}, offset=({offset_x},{offset_y}), "
            f"bin={bin_h}x{bin_v}{extra_text}"
        )

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

    def _call_list_parameters(self, client, timeout_s: float = 2.0):
        req = ListParameters.Request()
        req.prefixes = []
        req.depth = 0
        future = client.call_async(req)
        start_wait = time.time()
        while not future.done() and time.time() - start_wait < timeout_s:
            time.sleep(0.05)
        if not future.done():
            return None
        return future.result()

    def _get_declared_parameter_names(self, clients) -> set[str] | None:
        configured = self._configured_declared_parameter_names
        if configured is None:
            configured_json = self.params.as_str(
                "camera.driver_declared_parameters_json",
                "",
            ).strip()
            if configured_json:
                try:
                    parsed = json.loads(configured_json)
                    if isinstance(parsed, list):
                        configured = {
                            str(name).strip()
                            for name in parsed
                            if str(name).strip()
                        }
                    else:
                        configured = None
                except (TypeError, ValueError, json.JSONDecodeError):
                    configured = None
            self._configured_declared_parameter_names = configured

        cached_names = clients.get("declared_param_names")
        if isinstance(cached_names, set):
            if isinstance(configured, set):
                return configured.intersection(cached_names)
            return cached_names

        list_client = clients.get("list")
        if list_client is None:
            if isinstance(configured, set):
                return configured
            return None
        if not list_client.wait_for_service(timeout_sec=1.0):
            if isinstance(configured, set):
                return configured
            return None

        res = self._call_list_parameters(list_client)
        result = getattr(res, "result", None) if res is not None else None
        names = getattr(result, "names", None)
        if not isinstance(names, list):
            if isinstance(configured, set):
                return configured
            return None

        declared = {str(name) for name in names if name is not None}
        clients["declared_param_names"] = declared
        if isinstance(configured, set):
            return configured.intersection(declared)
        return declared

    def _call_set_parameter(
        self, client, name: str, value, timeout_s: float = 3.0
    ):
        if isinstance(value, bool):
            param_type = ParameterType.PARAMETER_BOOL
            kwargs = {"bool_value": bool(value)}
        elif isinstance(value, int) and not isinstance(value, bool):
            param_type = ParameterType.PARAMETER_INTEGER
            kwargs = {"integer_value": int(value)}
        elif isinstance(value, float):
            param_type = ParameterType.PARAMETER_DOUBLE
            kwargs = {"double_value": float(value)}
        else:
            param_type = ParameterType.PARAMETER_STRING
            kwargs = {"string_value": str(value)}
        req = SetParameters.Request()
        req.parameters = [
            Parameter(
                name=name,
                value=ParameterValue(
                    type=param_type,
                    **kwargs,
                ),
            )
        ]
        future = client.call_async(req)
        start_wait = time.time()
        while not future.done() and time.time() - start_wait < timeout_s:
            time.sleep(0.05)
        if not future.done():
            return False, "timeout while setting parameter"
        res = future.result()
        if not res or not res.results:
            return False, "empty response from set_parameters"
        first = res.results[0]
        return bool(first.successful), str(first.reason)

    def _to_python_value(self, param_value):
        if param_value.type == ParameterType.PARAMETER_INTEGER:
            return int(param_value.integer_value)
        if param_value.type == ParameterType.PARAMETER_DOUBLE:
            return float(param_value.double_value)
        if param_value.type == ParameterType.PARAMETER_BOOL:
            return bool(param_value.bool_value)
        if param_value.type == ParameterType.PARAMETER_STRING:
            return str(param_value.string_value)
        return None

    def _get_float_param(self, name: str, default: float) -> float:
        return self.params.as_float(name, default)

    def _get_int_param(self, name: str, default: int) -> int:
        return self.params.as_int(name, default)

    def _get_bool_param(self, name: str, default: bool) -> bool:
        return self.params.as_bool(name, default)

    def _is_switch_logging_enabled(self) -> bool:
        return self._get_bool_param("mtf.log_format_switch", True)

    @staticmethod
    def _float_or_default(value, default: float = 0.0) -> float:
        """Best-effort float conversion with a stable fallback."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _unpack_image_result(result):
        """Normalize fetch results to (image, timestamp)."""
        if not result:
            return None, None
        image = result[0]
        timestamp = result[1] if len(result) > 1 else None
        return image, timestamp

    @staticmethod
    def _collect_mismatches(actual: dict, target: dict, keys: list[str]) -> list[str]:
        """Return list of key mismatch diagnostics in the form key=actual!=target."""
        mismatches = []
        for key in keys:
            if key not in actual or key not in target:
                continue
            actual_value = actual[key]
            target_value = target[key]
            if isinstance(actual_value, float) or isinstance(target_value, float):
                matched = abs(float(actual_value) - float(target_value)) <= 1e-6
            elif isinstance(actual_value, bool) or isinstance(target_value, bool):
                matched = bool(actual_value) == bool(target_value)
            elif isinstance(actual_value, str) or isinstance(target_value, str):
                matched = str(actual_value) == str(target_value)
            else:
                matched = int(actual_value) == int(target_value)
            if not matched:
                mismatches.append(f"{key}={actual[key]}!={target[key]}")
        return mismatches

    @staticmethod
    def _resolve_auto_off_target(current_value):
        """Return a best-effort 'disabled' value for auto-style camera controls."""
        if isinstance(current_value, bool):
            return False
        return "Off"

    def _read_state_from_variants(
        self,
        variants,
        *,
        query_groups,
        required_keys: tuple[str, ...] = ("width", "height"),
    ):
        """Read current camera parameter state via small grouped parameter queries."""
        last_failure_reason = ""
        last_failure_rank = -1
        for set_service in self._param_set_services():
            clients = self._get_service_clients(set_service)
            set_client = clients["set"]
            get_client = clients["get"]
            if not set_client.wait_for_service(timeout_sec=1.0):
                reason = f"set service unavailable: {set_service}"
                rank = self._failure_reason_rank(reason)
                if rank >= last_failure_rank:
                    last_failure_reason = reason
                    last_failure_rank = rank
                continue
            if not get_client.wait_for_service(timeout_sec=1.0):
                reason = f"get service unavailable: {clients['get_service']}"
                rank = self._failure_reason_rank(reason)
                if rank >= last_failure_rank:
                    last_failure_reason = reason
                    last_failure_rank = rank
                continue

            declared_names = self._get_declared_parameter_names(clients)

            for names in variants:
                values = {}
                available_keys = set()
                types = {}
                saw_query = False
                for group in query_groups:
                    group_keys = [key for key in group if key in names]
                    if declared_names is not None:
                        group_keys = [
                            key for key in group_keys if names[key] in declared_names
                        ]
                    if not group_keys:
                        continue
                    saw_query = True
                    query_names = [names[key] for key in group_keys]
                    res = self._call_get_parameters(get_client, query_names)
                    if not res or not res.values or len(res.values) != len(query_names):
                        reason = (
                            f"empty/incomplete get_parameters response from {clients['get_service']} "
                            f"for names={query_names}"
                        )
                        rank = self._failure_reason_rank(reason)
                        if rank >= last_failure_rank:
                            last_failure_reason = reason
                            last_failure_rank = rank
                        continue
                    if all(v.type == ParameterType.PARAMETER_NOT_SET for v in res.values):
                        reason = (
                            f"all queried format params not-set on {clients['get_service']} "
                            f"for names={query_names}"
                        )
                        rank = self._failure_reason_rank(reason)
                        if rank >= last_failure_rank:
                            last_failure_reason = reason
                            last_failure_rank = rank
                        continue

                    for key, value_msg in zip(group_keys, res.values):
                        parsed = self._to_python_value(value_msg)
                        if parsed is None:
                            continue
                        values[key] = parsed
                        types[key] = value_msg.type
                        available_keys.add(key)

                if not saw_query or not values:
                    continue

                missing_required = [key for key in required_keys if key not in values]
                if missing_required:
                    reason = (
                        f"format params missing {missing_required} on {clients['get_service']}"
                    )
                    rank = self._failure_reason_rank(reason)
                    if rank >= last_failure_rank:
                        last_failure_reason = reason
                        last_failure_rank = rank
                    continue

                return {
                    "set_service": set_service,
                    "names": names,
                    "values": values,
                    "types": types,
                    "available_keys": sorted(available_keys),
                }

        if self._is_switch_logging_enabled() and last_failure_reason:
            self._node.get_logger().warn(
                f"Camera format read_state failed: {last_failure_reason}"
            )
        return None

    def read_state(self):
        """Read current ROI/Binning state from camera parameter services."""
        return self._read_state_from_variants(
            self.FORMAT_PARAM_NAME_VARIANTS,
            query_groups=self.FORMAT_QUERY_GROUPS,
            required_keys=("width", "height"),
        )

    def read_capture_state(self):
        """Read current MTF capture state including pixel format and gain if available."""
        return self._read_state_from_variants(
            self.CAPTURE_PARAM_NAME_VARIANTS,
            query_groups=self.CAPTURE_QUERY_GROUPS,
            required_keys=(),
        )

    def get_last_capture_state(self):
        """Return last readback state from MTF capture switch/restore."""
        return self._last_capture_state

    def get_last_operation_error(self) -> str:
        """Return the most recent camera-format operation error."""
        return str(self._last_operation_error or "")

    def build_mtf_capture_target(self, current_values: dict | None = None) -> dict:
        """Build the desired scientific MTF capture state from params/current readback."""
        current = dict(current_values or {})
        target = {
            "width": self._get_int_param(
                "mtf.capture_width",
                int(current.get("width", 5536)),
            ),
            "height": self._get_int_param(
                "mtf.capture_height",
                int(current.get("height", 3692)),
            ),
            "offset_x": self._get_int_param("mtf.capture_offset_x", 0),
            "offset_y": self._get_int_param("mtf.capture_offset_y", 0),
            "bin_h": self._get_int_param("mtf.capture_binning", 1),
            "bin_v": self._get_int_param("mtf.capture_binning", 1),
        }

        if not self._get_bool_param("mtf.use_raw_capture", True):
            return target

        target.update(self.build_mtf_scientific_capture_target(current))
        return target

    def build_mtf_scientific_capture_target(
        self,
        current_values: dict | None = None,
    ) -> dict:
        """Build the raw-only scientific capture state for MTF on the live stream."""
        current = dict(current_values or {})
        if not self._get_bool_param("mtf.use_raw_capture", True):
            return {}

        target = {}
        target["pixel_format"] = self.params.as_str(
            "mtf.capture_pixel_format",
            str(current.get("pixel_format", "BayerRG12")),
        )
        target_exposure = self._get_float_param(
            "mtf.capture_exposure_us",
            self._float_or_default(current.get("exposure_time"), 0.0),
        )
        if target_exposure > 0:
            target["exposure_time"] = target_exposure
        target["gain"] = self._get_float_param(
            "mtf.capture_gain",
            self._float_or_default(current.get("gain"), 0.0),
        )
        if self._get_bool_param("mtf.capture_disable_exposure_auto", True):
            target["exposure_auto"] = self._resolve_auto_off_target(
                current.get("exposure_auto", "Off")
            )
        if self._get_bool_param("mtf.capture_disable_gain_auto", True):
            target["gain_auto"] = self._resolve_auto_off_target(
                current.get("gain_auto", "Off")
            )
        if self._get_bool_param("mtf.capture_disable_white_balance_auto", True):
            target["white_balance_auto"] = self._resolve_auto_off_target(
                current.get("white_balance_auto", "Off")
            )
        if self._get_bool_param("mtf.capture_disable_gamma", True):
            target["gamma_enable"] = False
        if self._get_bool_param("mtf.capture_disable_color_transform", True):
            target["color_transform_enable"] = False
        return target

    def build_preview_restore_target(self, current_values: dict | None = None) -> dict:
        """Build the preview restore target used after MTF raw capture."""
        current = dict(current_values or {})
        target = {}
        default_pixel_format = self.params.as_str(
            "camera.default_pixel_format",
            str(current.get("pixel_format", "RGB8")),
        ).strip()
        if default_pixel_format:
            target["pixel_format"] = default_pixel_format
        return target

    def collect_scientific_capture_mismatches(
        self,
        state: dict | None,
        target_values: dict | None = None,
    ) -> list[str]:
        """Compare available scientific readbacks against the desired raw-MTF state."""
        if not state:
            return []

        actual_values = dict(state.get("values", state))
        available_keys = set(state.get("available_keys", actual_values.keys()))
        target = target_values or self.build_mtf_scientific_capture_target(actual_values)
        verify_keys = [
            key
            for key in self.SCIENTIFIC_CAPTURE_VERIFY_KEYS
            if key in actual_values and key in target and key in available_keys
        ]
        return self._collect_mismatches(actual_values, target, verify_keys)

    def _try_set_capture_without_state(
        self,
        target: dict,
        *,
        required_keys: tuple[str, ...] = (),
        best_effort_optional: bool = False,
    ) -> bool:
        """Fallback: try switching capture state even when current state is unreadable."""
        self._last_operation_error = ""
        for set_service in self._param_set_services():
            clients = self._get_service_clients(set_service)
            set_client = clients["set"]
            if not set_client.wait_for_service(timeout_sec=1.0):
                self._last_operation_error = f"set service unavailable: {set_service}"
                continue

            for names in self.CAPTURE_PARAM_NAME_VARIANTS:
                state_full = {
                    "set_service": set_service,
                    "names": names,
                    "available_keys": [
                        k
                        for k in (
                            "width",
                            "height",
                            "offset_x",
                            "offset_y",
                            "bin_h",
                            "bin_v",
                            "pixel_format",
                            "exposure_time",
                            "gain",
                            "exposure_auto",
                            "gain_auto",
                            "white_balance_auto",
                            "gamma",
                            "gamma_enable",
                            "color_transform_enable",
                        )
                        if k in names
                    ],
                }
                if self.set_capture_state(
                    state_full,
                    target,
                    required_keys=required_keys,
                    best_effort_optional=best_effort_optional,
                ):
                    if self._is_switch_logging_enabled():
                        self._node.get_logger().info(
                            f"Camera capture fallback switch succeeded via {set_service} with names={list(names.values())}"
                        )
                    return True
        return False

    def set_format(self, state: dict, target_values: dict) -> bool:
        """Apply target ROI/Binning values via parameter service."""
        filtered = {
            key: target_values[key]
            for key in ("width", "height", "offset_x", "offset_y", "bin_h", "bin_v")
            if key in target_values
        }
        return self.set_capture_state(state, filtered)

    def set_capture_state(
        self,
        state: dict,
        target_values: dict,
        *,
        required_keys: tuple[str, ...] = ("width", "height"),
        best_effort_optional: bool = False,
    ) -> bool:
        """Apply generic capture state updates via parameter service."""
        set_service = state.get("set_service")
        names = state.get("names", {})
        available_keys = set(state.get("available_keys", []))
        if not available_keys:
            # Backward compatibility with older state dicts.
            available_keys = set(names.keys())
        if not set_service or not names:
            return False

        clients = self._get_service_clients(set_service)
        set_client = clients["set"]
        if not set_client.wait_for_service(timeout_sec=1.0):
            self._last_operation_error = (
                f"Parameter service not available for camera capture switch: {set_service}"
            )
            self._node.get_logger().warn(
                self._last_operation_error
            )
            return False

        has_bin_controls = (
            "bin_h" in available_keys
            and "bin_v" in available_keys
            and "bin_h" in target_values
            and "bin_v" in target_values
        )
        target_binning = target_values.get("bin_h") if has_bin_controls else None
        if target_binning is not None and int(target_binning) <= 1:
            write_order = [
                "pixel_format",
                "exposure_auto",
                "gain_auto",
                "white_balance_auto",
                "gamma_enable",
                "color_transform_enable",
                "bin_h",
                "bin_v",
                "offset_x",
                "offset_y",
                "width",
                "height",
                "exposure_time",
                "gain",
                "gamma",
            ]
        elif target_binning is not None:
            write_order = [
                "pixel_format",
                "exposure_auto",
                "gain_auto",
                "white_balance_auto",
                "gamma_enable",
                "color_transform_enable",
                "offset_x",
                "offset_y",
                "width",
                "height",
                "bin_h",
                "bin_v",
                "exposure_time",
                "gain",
                "gamma",
            ]
        else:
            write_order = [
                "pixel_format",
                "exposure_auto",
                "gain_auto",
                "white_balance_auto",
                "gamma_enable",
                "color_transform_enable",
                "offset_x",
                "offset_y",
                "width",
                "height",
                "exposure_time",
                "gain",
                "gamma",
            ]

        write_keys = []
        for key in write_order:
            if (
                key not in target_values
                or key not in names
                or key not in available_keys
            ):
                continue
            write_keys.append(key)

        if self._is_switch_logging_enabled():
            optional_keys = {
                "offset_x",
                "offset_y",
                "bin_h",
                "bin_v",
                "pixel_format",
                "gain",
                "exposure_auto",
                "gain_auto",
                "white_balance_auto",
                "gamma",
                "gamma_enable",
                "color_transform_enable",
            }
            skipped_optional = [
                key
                for key in optional_keys
                if key in target_values and key in names and key not in write_keys
            ]
            if skipped_optional:
                self._node.get_logger().info(
                    f"Camera format switch: skipping unavailable optional keys {skipped_optional}"
                )

        for required in required_keys:
            if required in target_values and required not in write_keys:
                self._last_operation_error = (
                    f"Required camera capture key '{required}' is not available on parameter service."
                )
                self._node.get_logger().error(self._last_operation_error)
                return False

        if not write_keys:
            self._node.get_logger().warn(
                "No applicable camera capture keys available for update; keeping current format."
            )
            return True

        for key in write_keys:
            param_name = names[key]
            ok, reason = self._call_set_parameter(
                set_client,
                param_name,
                target_values[key],
            )
            if not ok:
                message = f"Failed to set {param_name}={target_values[key]}: {reason}"
                if key in required_keys or not best_effort_optional:
                    self._last_operation_error = message
                    self._node.get_logger().error(message)
                    return False
                self._node.get_logger().warn(message)

        self._last_operation_error = ""
        return True

    def switch_to_full_frame_for_mtf(
        self,
        last_ts_ns: int,
        get_latest_image_fn: Callable[[], tuple],
        wait_for_new_image_fn: Callable[..., tuple],
        *,
        live_geometry: tuple[int, int] | None = None,
    ):
        """Enable raw scientific capture on the current stream and return restore state."""
        self._last_capture_state = None
        self._last_operation_error = ""
        if not self._get_bool_param("mtf.use_raw_capture", True):
            return None, None

        requested_width = self._get_int_param("mtf.capture_width", 0)
        requested_height = self._get_int_param("mtf.capture_height", 0)
        if (
            live_geometry is not None
            and requested_width > 0
            and requested_height > 0
        ):
            live_width, live_height = [int(value) for value in live_geometry]
            if live_width == requested_width and live_height == requested_height:
                if self._is_switch_logging_enabled():
                    self._node.get_logger().info(
                        f"MTF raw capture: current stream geometry {live_width}x{live_height} "
                        "already matches requested geometry; skipping geometry switch."
                    )
            elif self._is_switch_logging_enabled():
                self._node.get_logger().warn(
                    f"MTF raw capture: current stream geometry {live_width}x{live_height} "
                    f"differs from requested {requested_width}x{requested_height}; "
                    "measuring anyway on the current stream."
                )

        state = self.read_capture_state()
        current = dict((state or {}).get("values", {}))
        restore_state = None
        if state is not None:
            restore_state = {
                "set_service": state.get("set_service"),
                "names": dict(state.get("names", {})),
                "values": dict(current),
                "types": dict(state.get("types", {})),
                "available_keys": list(state.get("available_keys", [])),
            }
            preview_target = self.build_preview_restore_target(current)
            restore_state["values"].update(
                {
                    key: value
                    for key, value in preview_target.items()
                    if key not in restore_state["values"]
                }
            )

        target = self.build_mtf_scientific_capture_target(current)
        if self._is_switch_logging_enabled():
            self._node.get_logger().info(
                f"MTF raw capture switch start: target={self._format_values(target)}"
            )

        can_write_pixel_format = (
            state is not None
            and "pixel_format" in set(state.get("available_keys", []))
        )
        if not can_write_pixel_format:
            if self._is_switch_logging_enabled():
                self._node.get_logger().warn(
                    "Could not read current camera PixelFormat state. "
                    "Trying fallback raw-capture switch without restore-state."
                )
            if not self._try_set_capture_without_state(
                target,
                required_keys=("pixel_format",),
                best_effort_optional=True,
            ):
                self._node.get_logger().warn(
                    "Fallback raw-capture switch failed. Proceeding to capture validation."
                )
                return restore_state, None
        elif not self.set_capture_state(
            state,
            target,
            required_keys=("pixel_format",),
            best_effort_optional=True,
        ):
            self._node.get_logger().warn(
                "Failed to switch camera to raw scientific capture state. "
                "Proceeding to capture validation."
            )
            return restore_state, None

        settle_s = self._get_float_param("mtf.capture_settle_s", 0.35)
        if settle_s > 0:
            time.sleep(settle_s)

        timeout_s = self._get_float_param("mtf.capture_image_timeout_s", 2.0)
        new_image, _ = self._unpack_image_result(
            wait_for_new_image_fn(last_ts_ns, timeout=timeout_s)
        )
        if new_image is None:
            new_image, _ = self._unpack_image_result(get_latest_image_fn())

        if self._is_switch_logging_enabled():
            applied_state = self.read_capture_state()
            self._last_capture_state = applied_state
            if applied_state:
                applied_values = applied_state.get("values", {})
                scientific_mismatches = self.collect_scientific_capture_mismatches(
                    applied_state,
                    target,
                )
                self._node.get_logger().info(
                    f"MTF raw capture switch applied: actual={self._format_values(applied_values)} "
                    f"service={applied_state.get('set_service', '?')}"
                )
                if scientific_mismatches:
                    self._node.get_logger().warn(
                        "MTF raw capture readback mismatch: "
                        + ", ".join(scientific_mismatches)
                        + " (MTF scientific mode may not be fully active)."
                    )
                else:
                    self._node.get_logger().info(
                        "MTF raw capture readback OK: requested scientific state active."
                    )
            else:
                self._node.get_logger().warn(
                    "MTF raw capture readback unavailable: failed to read camera state."
                )
            if new_image is not None:
                img_h, img_w = new_image.shape[:2]
                self._node.get_logger().info(
                    f"MTF raw capture image: {img_w}x{img_h}"
                )
            else:
                self._node.get_logger().warn(
                    "MTF raw capture image unavailable after switch; using latest cached image."
                )

        return restore_state, new_image

    def restore_after_mtf(self, restore_state: dict | None):
        """Restore camera ROI/Binning after MTF measurement."""
        if not self._get_bool_param("mtf.restore_after_measurement", True):
            return

        self._last_capture_state = None
        self._last_operation_error = ""
        target = dict((restore_state or {}).get("values", {}))
        if not target:
            target = self.build_preview_restore_target()
        if not target:
            return
        if self._is_switch_logging_enabled():
            self._node.get_logger().info(
                f"MTF format restore start: target={self._format_values(target)}"
            )

        restored = False
        if restore_state:
            restored = self.set_capture_state(
                restore_state,
                target,
                required_keys=("pixel_format",) if "pixel_format" in target else (),
                best_effort_optional=True,
            )
        else:
            restored = self._try_set_capture_without_state(
                target,
                required_keys=("pixel_format",) if "pixel_format" in target else (),
                best_effort_optional=True,
            )

        if not restored:
            self._node.get_logger().warn(
                "Failed to restore camera capture state after MTF."
            )
            return

        settle_s = self._get_float_param("mtf.restore_settle_s", 0.15)
        if settle_s > 0:
            time.sleep(settle_s)
        if self._is_switch_logging_enabled():
            restored_state = self.read_capture_state()
            self._last_capture_state = restored_state
            if restored_state:
                self._node.get_logger().info(
                    f"MTF format restore applied: actual={self._format_values(restored_state.get('values', {}))} "
                    f"service={restored_state.get('set_service', '?')}"
                )
            else:
                self._node.get_logger().warn(
                    "MTF format restore readback unavailable: failed to read camera state."
                )
