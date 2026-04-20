"""Helpers for runtime camera format switching (ROI/Binning)."""

from __future__ import annotations

import time
from typing import Callable

from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, SetParameters

from .base import ParameterAccessor


class CameraFormatController:
    """Encapsulates ROS parameter-based camera format changes."""

    PARAM_SET_SERVICES = (
        "/promoc/assembly_camera/set_parameters",
        "/promoc/assembly_camera_controller/set_parameters",
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

    def __init__(self, node):
        self._node = node
        self._service_clients = {}
        self.params = ParameterAccessor(node)
        self._last_capture_state = None

    def _get_service_clients(self, set_service: str):
        """Get cached set/get parameter clients for a service name."""
        cached = self._service_clients.get(set_service)
        if cached is not None:
            return cached

        get_service = set_service.replace("set_parameters", "get_parameters")
        cached = {
            "set": self._node.create_client(SetParameters, set_service),
            "get": self._node.create_client(GetParameters, get_service),
            "set_service": set_service,
            "get_service": get_service,
        }
        self._service_clients[set_service] = cached
        return cached

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
            extra.append(f"exp_us={exposure_time}")
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

    def _read_state_from_variants(self, variants):
        """Read current camera parameter state for a list of semantic name variants."""
        last_failure_reason = ""
        for set_service in self.PARAM_SET_SERVICES:
            clients = self._get_service_clients(set_service)
            set_client = clients["set"]
            get_client = clients["get"]
            if not set_client.wait_for_service(timeout_sec=1.0):
                last_failure_reason = f"set service unavailable: {set_service}"
                continue
            if not get_client.wait_for_service(timeout_sec=1.0):
                last_failure_reason = (
                    f"get service unavailable: {clients['get_service']}"
                )
                continue

            for names in variants:
                keys = list(names.keys())
                query_names = [names[k] for k in keys]
                res = self._call_get_parameters(get_client, query_names)
                if not res or not res.values or len(res.values) != len(query_names):
                    last_failure_reason = (
                        f"empty/incomplete get_parameters response from {clients['get_service']} "
                        f"for names={query_names}"
                    )
                    continue
                if all(v.type == ParameterType.PARAMETER_NOT_SET for v in res.values):
                    last_failure_reason = (
                        f"all queried format params not-set on {clients['get_service']} "
                        f"for names={query_names}"
                    )
                    continue

                values = {}
                available_keys = set()
                types = {}
                for key, value_msg in zip(keys, res.values):
                    parsed = self._to_python_value(value_msg)
                    if parsed is not None:
                        values[key] = parsed
                        types[key] = value_msg.type
                        available_keys.add(key)

                if "width" not in values or "height" not in values:
                    last_failure_reason = (
                        f"format params missing width/height on {clients['get_service']} "
                        f"for names={query_names}"
                    )
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
        return self._read_state_from_variants(self.FORMAT_PARAM_NAME_VARIANTS)

    def read_capture_state(self):
        """Read current MTF capture state including pixel format and gain if available."""
        return self._read_state_from_variants(self.CAPTURE_PARAM_NAME_VARIANTS)

    def get_last_capture_state(self):
        """Return last readback state from MTF capture switch/restore."""
        return self._last_capture_state

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
        target = target_values or self.build_mtf_capture_target(actual_values)
        verify_keys = [
            key
            for key in self.SCIENTIFIC_CAPTURE_VERIFY_KEYS
            if key in actual_values and key in target and key in available_keys
        ]
        return self._collect_mismatches(actual_values, target, verify_keys)

    def _try_set_capture_without_state(self, target: dict) -> bool:
        """Fallback: try switching capture state even when current state is unreadable."""
        for set_service in self.PARAM_SET_SERVICES:
            clients = self._get_service_clients(set_service)
            set_client = clients["set"]
            if not set_client.wait_for_service(timeout_sec=1.0):
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
                if self.set_capture_state(state_full, target):
                    if self._is_switch_logging_enabled():
                        self._node.get_logger().info(
                            f"Camera capture fallback switch succeeded via {set_service} with names={list(names.values())}"
                        )
                    return True

                # Retry with minimal required keys only (width/height)
                state_min = {
                    "set_service": set_service,
                    "names": names,
                    "available_keys": [k for k in ("width", "height") if k in names],
                }
                minimal_target = {
                    k: target[k] for k in ("width", "height") if k in target
                }
                if self.set_format(state_min, minimal_target):
                    if self._is_switch_logging_enabled():
                        self._node.get_logger().info(
                            f"Camera capture fallback switch (minimal) succeeded via {set_service} with names={list(names.values())}"
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

    def set_capture_state(self, state: dict, target_values: dict) -> bool:
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
            self._node.get_logger().warn(
                f"Parameter service not available for camera capture switch: {set_service}"
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

        for required in ("width", "height"):
            if required in target_values and required not in write_keys:
                self._node.get_logger().error(
                    f"Required camera capture key '{required}' is not available on parameter service."
                )
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
                self._node.get_logger().error(
                    f"Failed to set {param_name}={target_values[key]}: {reason}"
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
        self._last_capture_state = None
        if not self._get_bool_param("mtf.use_full_frame", False):
            return None, None

        state = self.read_capture_state()
        if state is None:
            target = self.build_mtf_capture_target()
            if self._is_switch_logging_enabled():
                self._node.get_logger().warn(
                    "Could not read current camera ROI/Binning state. "
                    "Trying fallback full-frame switch without restore-state."
                )
            if not self._try_set_capture_without_state(target):
                self._node.get_logger().warn(
                    "Fallback capture switch failed. Proceeding with current image for MTF."
                )
                return None, None

            settle_s = self._get_float_param("mtf.capture_settle_s", 0.35)
            if settle_s > 0:
                time.sleep(settle_s)

            timeout_s = self._get_float_param("mtf.capture_image_timeout_s", 2.0)
            new_image, _ = self._unpack_image_result(
                wait_for_new_image_fn(last_ts_ns, timeout=timeout_s)
            )
            if new_image is None:
                new_image, _ = self._unpack_image_result(get_latest_image_fn())

            self._last_capture_state = self.read_capture_state()
            if self._is_switch_logging_enabled() and new_image is not None:
                img_h, img_w = new_image.shape[:2]
                self._node.get_logger().info(
                    f"MTF fallback capture image: {img_w}x{img_h}"
                )
            return None, new_image

        current = dict(state.get("values", {}))
        restore_state = {
            "set_service": state.get("set_service"),
            "names": dict(state.get("names", {})),
            "values": current,
            "types": dict(state.get("types", {})),
            "available_keys": list(state.get("available_keys", [])),
        }

        target = self.build_mtf_capture_target(current)
        if self._is_switch_logging_enabled():
            self._node.get_logger().info(
                f"MTF format switch start: current={self._format_values(current)} "
                f"target={self._format_values(target)}"
            )

        if not self.set_capture_state(state, target):
            self._node.get_logger().warn(
                "Failed to switch camera to MTF capture state. "
                "Proceeding with current image for MTF."
            )
            return None, None

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
                verify_keys = [
                    key
                    for key in ("width", "height", "offset_x", "offset_y")
                    if key in applied_values and key in target
                ]
                geometry_mismatches = self._collect_mismatches(
                    applied_values, target, verify_keys
                )
                scientific_mismatches = self.collect_scientific_capture_mismatches(
                    applied_state,
                    target,
                )
                mismatches = geometry_mismatches + scientific_mismatches
                self._node.get_logger().info(
                    f"MTF format switch applied: actual={self._format_values(applied_values)} "
                    f"service={applied_state.get('set_service', '?')}"
                )
                if mismatches:
                    self._node.get_logger().warn(
                        "MTF format switch readback mismatch: "
                        + ", ".join(mismatches)
                        + " (MTF scientific mode may not be fully active)."
                    )
                else:
                    self._node.get_logger().info(
                        "MTF format switch readback OK: requested capture state active."
                    )
            else:
                self._node.get_logger().warn(
                    "MTF format switch readback unavailable: failed to read camera state."
                )
            if new_image is not None:
                img_h, img_w = new_image.shape[:2]
                self._node.get_logger().info(
                    f"MTF format switch image: {img_w}x{img_h}"
                )
            else:
                self._node.get_logger().warn(
                    "MTF format switch image unavailable after switch; using latest cached image."
                )

        return restore_state, new_image

    def restore_after_mtf(self, restore_state: dict):
        """Restore camera ROI/Binning after MTF measurement."""
        if not restore_state:
            return
        if not self._get_bool_param("mtf.restore_after_measurement", True):
            return

        self._last_capture_state = None
        target = dict(restore_state.get("values", {}))
        if not target:
            return
        if self._is_switch_logging_enabled():
            self._node.get_logger().info(
                f"MTF format restore start: target={self._format_values(target)}"
            )

        if not self.set_capture_state(restore_state, target):
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
