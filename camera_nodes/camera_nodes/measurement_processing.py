"""ROS-independent verification of linear scientific camera processing."""

from __future__ import annotations


class ProcessingStateError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def verify_processing_state(values, unsupported, pixel_format):
    """Verify processing readbacks and return features proven absent on-device."""
    unsupported = set(unsupported or ())
    for key in (
        "exposure_auto", "gain_auto", "white_balance_auto",
        "gamma_enable", "color_transform_enable",
    ):
        if key in values and str(values[key]).lower() not in ("off", "false", "0", "0.0"):
            raise ProcessingStateError("AUTOMATIC_PROCESSING", f"{key} must be off")
    if "gamma_enable" not in values:
        if "gamma" in values:
            if abs(float(values["gamma"])-1) > 1e-6:
                raise ProcessingStateError("AUTOMATIC_PROCESSING", "Gamma must be unity")
        elif not ({"gamma", "gamma_enable"} & unsupported):
            raise ProcessingStateError(
                "PROCESSING_UNVERIFIED", "Gamma must be verified off or unity"
            )
    if str(pixel_format).startswith("Bayer"):
        if "white_balance_auto" not in values:
            raise ProcessingStateError(
                "PROCESSING_UNVERIFIED", "Bayer white-balance readback required"
            )
        if (
            "color_transform_enable" not in values
            and "color_transform_enable" not in unsupported
        ):
            raise ProcessingStateError(
                "PROCESSING_UNVERIFIED", "Bayer color-transform readback required"
            )
    return sorted(
        unsupported & {"gamma", "gamma_enable", "color_transform_enable"}
    )
